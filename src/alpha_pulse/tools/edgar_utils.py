"""Utility functions for SEC EDGAR API interactions."""

import pandas as pd
from bs4 import BeautifulSoup
import re
from typing import Optional
from dataclasses import dataclass

from alpha_pulse.types.edgar8k import ExtractedUrls

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

def parse_atom_latest_filings_feed(response: str) -> pd.DataFrame:
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
        
        parsed_data.append(AtomEntry(
            cik=extract_cik_from_title(title.text),
            base_url=link["href"] if link.has_attr("href") else None,
            item_list=item_list,
            updated_date=updated.text,
            date=extract_date_from_summary(summary.text)
        ))
    
    return pd.DataFrame([vars(entry) for entry in parsed_data])