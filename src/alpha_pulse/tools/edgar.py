"""SEC EDGAR API client for retrieving and parsing company filings."""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from alpha_pulse.types.edgar import Edgar8kFilingData
from alpha_pulse.tools.edgar_utils import parse_atom_latest_filings_feed, filter_8k_feed_by_items, extract_8k_url_from_base_url

from langchain.tools import tool


# Constants
SEC_BASE_URL = "https://www.sec.gov"
SEC_API_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept-Encoding": "gzip, deflate",
}


class Edgar8kFilingInput(BaseModel):
    """Input model for parsing 8-K filings.
    
    Attributes:
        ticker: Stock ticker symbol to analyze
    """
    ticker: str = Field(description="Stock ticker symbol (e.g., 'AAPL' for Apple)")


@dataclass
class SECClient:
    """Client for interacting with SEC EDGAR API.
    
    Attributes:
        base_url: Base URL for SEC website
        api_base_url: Base URL for SEC API
        headers: HTTP headers for SEC requests
    """
    base_url: str = SEC_BASE_URL
    api_base_url: str = SEC_API_BASE_URL
    headers: Dict[str, str] = field(default_factory=lambda: SEC_HEADERS.copy())

    async def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Make an async request to the SEC API with proper headers.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            
        Returns:
            str: Response text from the SEC API
            
        Raises:
            aiohttp.ClientError: If the request fails
        """
        headers = headers or self.headers
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.text()

    async def _make_json_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict:
        """Make an async request to the SEC API and parse JSON response.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            
        Returns:
            Dict: Parsed JSON response
            
        Raises:
            aiohttp.ClientError: If the request fails
            ValueError: If the response is not valid JSON
        """
        headers = headers or self.headers
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()


class EdgarAPI:
    """Main class for interacting with SEC EDGAR API.
    
    This class provides methods to:
    - Look up company CIKs from ticker symbols
    - Retrieve 8-K filing URLs and metadata
    - Parse 8-K filing content
    """
    
    def __init__(self) -> None:
        """Initialize the EdgarAPI with a SECClient instance."""
        self.client = SECClient()
    
    async def get_latest_filings(self, limit: int = 40, filing_type: str = '8-K') -> List[str]:
        """Retrieves the latest filings from the SEC.
        
        Args:
            limit: Maximum number of filings to return (default: 40)
            filing_type: Type of filing to retrieve (default: '8-K')
        """
        headers = {
            'User-Agent': os.getenv("USER_AGENT"),
            'Accept-Encoding': 'gzip, deflate',
        }
        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&owner=include&count={limit}&action=getcurrent&output=atom"
        resp: str = await self.client._make_request(url, headers)
        df = parse_atom_latest_filings_feed(resp)
        filtered_df = filter_8k_feed_by_items(df)

        async def get_8k_url(x)->str:
            html = await self.client._make_request(x, headers)
            return extract_8k_url_from_base_url(html)
        
        filtered_df['url_8k'] = await asyncio.gather(*[get_8k_url(x) for x in filtered_df['base_url']])
        return filtered_df


    async def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Retrieves the Central Index Key (CIK) for a given stock ticker symbol.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL' for Apple)
            
        Returns:
            Optional[str]: 10-digit CIK number with leading zeros if found, None otherwise
        """
        url = f"{self.client.base_url}/files/company_tickers.json"
        data = await self.client._make_json_request(url)
        
        for entry in data.values():
            if entry['ticker'] == ticker.upper():
                cik = str(entry['cik_str']).zfill(10)
                logging.info(f"CIK found for {ticker}: {cik}")
                return cik
        return None

    async def _get_8k_root_info(self, cik: str, limit: int = 3) -> List[Edgar8kFilingData]:
        """Retrieves list of the (limit) most recent 8-K root urls 
           (root-urls are the 'home-page' for all metadata & filing links for a specific 8k).
        
        Args:
            cik: Central Index Key of the company
            limit: Maximum number of filings to return (default: 3)
            
        Returns:
            Edgar8kFilingUrls: Container with list of filing URLs and metadata
            
        Raises:
            aiohttp.ClientError: If the SEC API request fails
        """
        cik_padded = cik.zfill(10)
        url = f'{self.client.api_base_url}/submissions/CIK{cik_padded}.json'
        logging.info(f"Retrieving 8-K root urls for ({cik}) from {url}")
        
        data = await self.client._make_json_request(url)

        filings = data.get('filings', {}).get('recent', {})
        accession_numbers = filings.get('accessionNumber', [])
        filing_dates = filings.get('filingDate', [])
        form_types = filings.get('form', [])
        item_types = filings.get('items', [])

        results = []
        for accession_number, filing_date, form_type, item_type in zip(accession_numbers, filing_dates, form_types, item_types):
            if form_type == '8-K':
                accession_number_nodashes = accession_number.replace('-', '')
                filing_url = f"{self.client.base_url}/Archives/edgar/data/{int(cik)}/{accession_number_nodashes}/{accession_number}-index.htm"
                results.append(
                    Edgar8kFilingData(
                        cik = cik_padded,
                        filing_date=filing_date,
                        root_url=filing_url,
                        item_type=item_type.split(',') if item_type else [],
                    )
                )
                if len(results) >= limit:
                    break

        return results

    async def _get_filing_urls_from_root_url(self, root_url: str) -> Tuple[str, List[str]]:
        """
        When provided a root url, this method will retrieve the url link to the
        actual 8-K filing text record.
        
        Args:
            root_url: URL of the filing index page
            
        Returns:
            str: URL of the 8-K text document
            
        Raises:
            aiohttp.ClientError: If the request fails
            ValueError: If the 8-K text link cannot be found
        """
        logging.info(f"Extracting 8-K text link from {root_url}")

        headers = {
            'User-Agent': os.getenv("USER_AGENT"),
            'Accept-Encoding': 'gzip, deflate',
        }

        html = await self.client._make_request(root_url, headers)
        soup = BeautifulSoup(html, 'html.parser')

        # Find all table rows in the document
        rows = soup.find_all('tr')

        filing_url = ''
        ex99_urls = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                file_type = cols[3].get_text(strip=True)
                if '8-k' in file_type.lower() and not filing_url:
                    link_tag = cols[2].find('a')
                    href = link_tag['href'] if link_tag and 'href' in link_tag.attrs else None
                    filing_url = SEC_BASE_URL + href.replace('ix?doc=', '')
                if 'ex-99' in file_type.lower():
                    link_tag = cols[2].find('a')
                    href = link_tag['href'] if link_tag and 'href' in link_tag.attrs else None
                    ex99_urls.append(SEC_BASE_URL + href.replace('ix?doc=', ''))
        if not filing_url:
            raise ValueError(f"Could not find 8-K text link in {root_url}")
        return filing_url, ex99_urls

    async def _load_raw_text(self, url: str) -> str:
        """Load's the raw text from the 8-K or EX-99.n filing url.
        
        Args:
            url: URL of the 8-K or EX-99.n filing document
            
        Returns:
            str: dump of the raw text from the 8-K or EX-99.n filing url
            
        Raises:
            aiohttp.ClientError: If the filing document request fails
        """
        html = await self.client._make_request(url)
        soup = BeautifulSoup(html, 'html.parser')
        document_text = soup.get_text()
        return document_text


    async def retrieve_8k_filings(self, ticker: str='', cik:str='', limit:int=3) -> List[Edgar8kFilingData]:
        """Parses the latest 8-K filing for a given ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL' for Apple)
            
        Returns:
            dict: Dictionary with filing sections as keys and their content as values
            
        Raises:
            ValueError: If no CIK is found for the ticker or no 8-K filings exist
            aiohttp.ClientError: If any HTTP request fails
        """

        if not cik and not (cik:=await self.get_cik_from_ticker(ticker)):
            raise ValueError(f"No CIK found for ticker: {ticker}")
        
        root_info:List[Edgar8kFilingData] = await self._get_8k_root_info(cik, limit)
        if not root_info:
            raise ValueError(f"No 8-K filings found for ({ticker},{cik})")
        
        # Process all entries in parallel
        async def process_entry(entry: Edgar8kFilingData) -> Edgar8kFilingData:
            filing_url, ex99_urls = await self._get_filing_urls_from_root_url(entry.root_url)
            entry.filing_url = filing_url
            entry.ex99_urls = ex99_urls
            entry.raw_text = await self._load_raw_text(filing_url)
            entry.raw_ex99_texts = await asyncio.gather(*[self._load_raw_text(url) for url in ex99_urls])
            return entry

        # Create tasks for all entries
        tasks = [process_entry(entry) for entry in root_info]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any errors and return successful results
        processed_entries = []
        for result in results:
            if isinstance(result, Exception):
                logging.error(f"Error processing entry: {str(result)}")
                continue
            processed_entries.append(result)
            
        return processed_entries


#@tool("parse_latest_8k_filing", args_schema=Edgar8kFilingInput)
async def parse_latest_8k_filing_tool(ticker: str, limit: int = 3) -> List[Edgar8kFilingData]:
    """Parse the latest 8-K filing for a given ticker.
    
    Args:
        ticker: The stock ticker symbol of the company
        
    Returns:
        List[Edgar8kFilingData]: A list of Edgar8kFilingData objects containing the filing text and metadata
    """
    return await EdgarAPI().retrieve_8k_filings(ticker, limit=limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = asyncio.run(EdgarAPI().get_latest_filings())
    print(df.head())