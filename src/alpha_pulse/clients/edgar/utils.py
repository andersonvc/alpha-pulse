"""Utility functions for SEC EDGAR API interactions."""

import pandas as pd
from bs4 import BeautifulSoup
import re
from typing import Optional, List
from dataclasses import dataclass
from typing import Dict
from html import unescape

from alpha_pulse.types.edgar8k import ExtractedUrls
from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
# Constants
SEC_BASE_URL = 'https://www.sec.gov'
ALLOWED_8K_ITEMS = {
    '2.02', '1.01', '5.02', '2.01', '8.01', '1.03',
    '3.01', '4.02', '2.03', '5.03', '4.01', '5.07',
}

@dataclass
class AtomEntry:
    """Represents an entry from the SEC's Atom feed."""
    cik: str
    base_url: str
    item_list: str
    updated_date: str
    date: str

def extract_cik_from_title(title: str) -> Optional[str]:
    """Extract CIK from title string.
    
    Args:
        title: Title string containing CIK
        
    Returns:
        Optional[str]: Extracted CIK or None if not found
    """
    match = re.search(r'\(([^()]+)\)', title)
    return match.group(1) if match else None

def extract_date_from_summary(summary_text: str) -> Optional[str]:
    """Extract filing date from summary text.
    
    Args:
        summary_text: Summary text containing filing date
        
    Returns:
        Optional[str]: Extracted date or None if not found
    """
    match = re.search(r'Filed:.*?\s*(\d{4}-\d{2}-\d{2})', summary_text)
    return match.group(1) if match else None

def filter_8k_feed_by_items(df: pd.DataFrame) -> pd.DataFrame:
    """Filter the 8-K feed to only include filings with material events.
    
    Args:
        df: DataFrame containing 8-K filings
        
    Returns:
        DataFrame filtered to include only material events
    """
    df['filtered_items'] = df['item_list'].apply(
        lambda x: ','.join(item for item in x.split(',') if item in ALLOWED_8K_ITEMS)
    )
    return df

def extract_8k_url_from_base_url(response: str) -> ExtractedUrls:
    """Extract the 8-K URL from the base URL response.
    
    Args:
        response: HTML response from base URL
        
    Returns:
        ExtractedUrls object containing URLs
        
    Raises:
        ValueError: If 8-K URL cannot be found
    """
    soup = BeautifulSoup(response, 'html.parser')
    filing_url = ''
    ex99_urls = []
    
    for row in soup.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
            
        file_type = cols[3].get_text(strip=True).lower()
        link_tag = cols[2].find('a')
        if not link_tag or 'href' not in link_tag.attrs:
            continue
            
        href = link_tag['href'].replace('ix?doc=', '')
        
        if '8-k' in file_type and not filing_url:
            filing_url = SEC_BASE_URL + href
        elif 'ex-99' in file_type:
            ex99_urls.append(SEC_BASE_URL + href)

    if not filing_url:
        raise ValueError("Could not find 8-K text link in base URL")
    
    return ExtractedUrls(
        url_8k=filing_url,
        url_ex99=','.join(ex99_urls)
    )

def parse_atom_latest_filings_feed(response: str) -> List[FilingRSSFeedEntry]:
    """Parse the SEC's Atom feed for latest filings.
    
    Args:
        response: XML response from Atom feed
        
    Returns:
        DataFrame containing parsed filing information
    """
    soup = BeautifulSoup(response, "xml")
    entries = soup.find_all("entry")
    item_pattern = re.compile(r"Item\s\d+\.\d{2}")
    
    parsed_data = []
    for entry in entries:
        title = entry.find("title")
        link = entry.find("link")
        updated = entry.find("updated")
        summary = entry.find("summary")
        
        if not all([title, link, updated, summary]):
            continue
            
        # Extract item list from summary
        item_list = ",".join(sorted(set(
            item.replace("Item ", "")
            for item in item_pattern.findall(summary.text)
        )))
        
        rss_record = FilingRSSFeedEntry(
            cik=extract_cik_from_title(title.text),
            base_url=link["href"] if link.has_attr("href") else None,
            item_list=item_list,
            ts=updated.text,
            filing_date=updated.text.split("T")[0]
        )
        parsed_data.append(rss_record)

    return parsed_data

def extract_8k_url_from_base_url(response: str) -> tuple[str, str]:
    """Extract the 8-K URL from the base URL response.
    
    Args:
        response: HTML response from base URL
        
    Returns:
        ExtractedUrls object containing URLs
        
    Raises:
        ValueError: If 8-K URL cannot be found
    """
    soup = BeautifulSoup(response, 'html.parser')
    url_8k = ''
    urls_ex99 = []
    
    for row in soup.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
            
        file_type = cols[3].get_text(strip=True).lower()
        link_tag = cols[2].find('a')
        if not link_tag or 'href' not in link_tag.attrs:
            continue
            
        href = link_tag['href'].replace('ix?doc=', '')
        
        if '8-k' in file_type and not url_8k:
            url_8k = SEC_BASE_URL + href
        elif 'ex-99' in file_type:
            urls_ex99.append(SEC_BASE_URL + href)
    
    if not url_8k:
        raise ValueError("Could not find 8-K text link in base URL")
    urls_ex99 = ','.join(urls_ex99)

    return (url_8k, urls_ex99)


def clean_text(text: str) -> str:
    """Clean up strange characters, whitespace, and HTML artifacts."""
    text = unescape(text)

    # Replace weird unicode entities
    replacements = {
        '\u00a0': ' ',  # non-breaking space
        '\u2001': ' ',  # em space
        '\u2002': ' ',  # en space
        '\u2003': ' ',  # 3-em space
        '\u2009': ' ',  # thin space
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u2014': '-',  # em dash
        '\u2013': '-',  # en dash
        '\u2026': '...',  # ellipsis
        '\u2022': '-',  # bullet
        '\u00b7': '-',  # middle dot
        '&#8211;': '-', # dash
        '&#8217;': "'", # apostrophe
        '&#8220;': '"', # left double quote
        '&#8221;': '"', # right double quote
        '&#160;': ' ',  # space
        '&#8201;': ' ', # thin space
        '&#8194;': ' ', # en space
        '&#8195;': ' ', # em space
        '&#8722;': '-', # minus
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def clean_and_extract_normalized_sections(raw_text: str) -> Dict[str, str]:
    """
    Clean HTML, normalize strange characters, and split into sections by Item number.
    """
    if not raw_text:
        return {}

    # Step 1: Unescape and basic clean
    text = clean_text(raw_text)

    # Step 2: Remove XML headers
    text = re.sub(r'<\?.*?\?>', '', text)

    # Step 3: Parse HTML
    soup = BeautifulSoup(text, "lxml")

    body = soup.find('body')
    if body:
        soup = body

    for tag in soup(["script", "style", "head", "meta", "link", "hidden", "ix:header", "ix:hidden", "ix:references", "ix:resources"]):
        tag.decompose()

    for p in soup.find_all(['p', 'div', 'br', 'tr']):
        p.insert_before("\n")

    # Step 4: Get plain text
    plain_text = soup.get_text(separator=' ')
    plain_text = clean_text(plain_text)  # extra normalization pass

    # Step 5: Normalize 'Item' casing
    plain_text = re.sub(r'ITEM', 'Item', plain_text, flags=re.IGNORECASE)

    # Step 6: Find sections
    section_pattern = re.compile(r'(Item\s+\d+\.\d+[^A-Za-z0-9]+.*?) (?=Item\s+\d+\.\d+[^A-Za-z0-9]+|$)', re.IGNORECASE)
    matches = section_pattern.finditer(plain_text)

    sections = {}
    for match in matches:
        section_text = match.group(1).strip()
        item_match = re.match(r'Item\s+(\d+\.\d+)', section_text, re.IGNORECASE)
        if item_match:
            normalized_item = f"{item_match.group(1)}"
            sections[normalized_item] = section_text

    return sections

def parse_document_string(doc_string):
    # Find all <DOCUMENT>...</DOCUMENT> blocks
    document_blocks = re.findall(r'<DOCUMENT>(.*?)</DOCUMENT>', doc_string, re.DOTALL | re.IGNORECASE)

    parsed_documents = []

    for block in document_blocks:
        doc_info = {}

        # Extract metadata
        fields = ['TYPE', 'SEQUENCE', 'FILENAME', 'DESCRIPTION']
        for field in fields:
            match = re.search(rf'<{field}>(.*)', block)
            if match:
                doc_info[field.lower()] = match.group(1).strip()
            else:
                doc_info[field.lower()] = None

        # Extract <TEXT> content
        text_match = re.search(r'<TEXT>(.*)', block, re.DOTALL | re.IGNORECASE)
        if text_match:
            raw_text = text_match.group(1).strip()

            # Try to extract <BODY> if it's HTML
            soup = BeautifulSoup(raw_text, 'html.parser')

            body = soup.find('body')
            if body:
                # Extract text from HTML body
                cleaned_text = body.get_text(separator='\n', strip=True)
            else:
                cleaned_text = soup.get_text(separator='\n', strip=True)

            # Unescape HTML entities like &ldquo;
            cleaned_text = unescape(cleaned_text)

            doc_info['text'] = cleaned_text
        else:
            doc_info['text'] = None

        parsed_documents.append(doc_info)

    return clean_text('\n'.join([doc['text'] for doc in parsed_documents])).strip()


def extract_exhibit_number(url: str) -> Optional[str]:
    patterns = [
        r"ex\d+-(\d+)",
        r"ex99+(\d+)",
        r"ex-99(\d+)",
        r"exhibit99(\d+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    print(f"No match found for {url}")
    return None

import threading

class SharedSingletonSet:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SharedSingletonSet, cls).__new__(cls)
                cls._instance._init_set()
        return cls._instance

    def _init_set(self):
        self._set = set()
        self._set_lock = threading.Lock()

    def add(self, item):
        with self._set_lock:
            self._set.add(item)

    def remove(self, item):
        with self._set_lock:
            self._set.remove(item)

    def contains(self, item):
        with self._set_lock:
            return item in self._set

    def get_all(self):
        with self._set_lock:
            return set(self._set)

