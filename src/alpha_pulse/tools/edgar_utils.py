import pandas as pd
from bs4 import BeautifulSoup
import re

SEC_BASE_URL = 'https://www.sec.gov'

def extract_cik_from_title(title: str) -> str:
    match = re.search(r'\(([^()]+)\)', title)
    return match.group(1) if match else None

def extract_date_from_summary(summary_text:str):
    match = re.search(r'Filed:.*?\s*(\d{4}-\d{2}-\d{2})', summary_text)
    return match.group(1) if match else None

def filter_8k_feed_by_items(df:pd.DataFrame):
    """Filter the 8-K feed to only include filings with material events (ie those with the following list)."""
    allowed_items = {
        '2.02',
        '1.01',
        '5.02',
        '2.01',
        '8.01',
        '1.03',
        '3.01',
        '4.02',
        '2.03',
        '5.03',
        '4.01',
        '5.07',
    }
    
    df['filtered_items'] = df['item_list'].apply(lambda x: ','.join([item for item in x.split(',') if item in allowed_items]))
    return df

def extract_8k_url_from_base_url(response:str)->str:
    """Extract the 8-K url from the base url response."""
    soup = BeautifulSoup(response, 'html.parser')

    # Find all table rows in the document
    rows = soup.find_all('tr')

    filing_url = ''
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 4:
            file_type = cols[3].get_text(strip=True)
            if '8-k' in file_type.lower() and not filing_url:
                link_tag = cols[2].find('a')
                href = link_tag['href'] if link_tag and 'href' in link_tag.attrs else None
                filing_url = SEC_BASE_URL + href.replace('ix?doc=', '')
                break

    if not filing_url:
        raise ValueError(f"Could not find 8-K text link in from base url.")

    return filing_url


def parse_atom_latest_filings_feed(response:str):

    # Parse the XML content using BeautifulSoup
    soup = BeautifulSoup(response, "xml")
    
    # Extract all <entry> elements (Atom format)
    entries = soup.find_all("entry")
    
    # Regular expression to capture "Item X.XX"
    item_pattern = re.compile(r"Item\s\d+\.\d{2}")
    
    # Prepare list to store parsed data
    parsed_data = []
    
    for entry in entries:
        title = entry.find("title").text if entry.find("title") else None
        url = entry.find("link")["href"] if entry.find("link") and entry.find("link").has_attr("href") else None
        updated_date = entry.find("updated").text if entry.find("updated") else None
        summary = entry.find("summary").text if entry.find("summary") else ""
        
        # Extract item list from summary
        item_list_matches = item_pattern.findall(summary)
        item_list_matches = [item.replace("Item ", "") for item in item_list_matches]
        item_list = ",".join(sorted(set(item_list_matches)))

        parsed_data.append({
            "cik":extract_cik_from_title(title),
            "base_url": url,
            "item_list": item_list,
            "updated_date": updated_date,
            "date": extract_date_from_summary(summary),
        })
    
    # Convert list of dicts to DataFrame
    df = pd.DataFrame(parsed_data)
    return df