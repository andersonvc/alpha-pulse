"""SEC EDGAR API client for retrieving and parsing company filings."""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import time
from threading import Lock

import pandas as pd
import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from alpha_pulse.tools.edgar_utils import (
    parse_atom_latest_filings_feed,
    filter_8k_feed_by_items,
    extract_8k_url_from_base_url
)
from alpha_pulse.types.edgar8k import ExtractedUrls

# Constants
SEC_BASE_URL = "https://www.sec.gov"
SEC_API_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept-Encoding": "gzip, deflate",
}
# SEC rate limits: 10 requests per second, but with a more conservative approach
SEC_RATE_LIMIT = 0.2  # 5 requests per second
SEC_BURST_LIMIT = 10  # Maximum number of requests in a burst
SEC_BURST_WINDOW = 1.0  # Time window for burst limit in seconds


class RateLimiter:
    """Thread-safe rate limiter for SEC requests."""
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.last_request_time = 0.0
                cls._instance.request_times = []
        return cls._instance
    
    async def wait(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Clean up old request times
        self.request_times = [t for t in self.request_times if now - t < SEC_BURST_WINDOW]
        
        # Check burst limit
        if len(self.request_times) >= SEC_BURST_LIMIT:
            wait_time = self.request_times[0] + SEC_BURST_WINDOW - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.request_times = self.request_times[1:]
        
        # Check rate limit
        elapsed = now - self.last_request_time
        if elapsed < SEC_RATE_LIMIT:
            await asyncio.sleep(SEC_RATE_LIMIT - elapsed)
        
        # Update tracking
        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)


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
    _last_request_time: float = 0.0
    _min_request_interval: float = 1.0 / 8.0  # 8 requests per second (more conservative)
    _request_times: List[float] = field(default_factory=list)
    _burst_window: float = 1.0  # 1 second window
    _max_burst: int = 8  # Maximum requests in burst window

    async def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Clean up old request times
        self._request_times = [t for t in self._request_times if now - t < self._burst_window]
        
        # Check burst limit
        if len(self._request_times) >= self._max_burst:
            wait_time = self._request_times[0] + self._burst_window - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._request_times = self._request_times[1:]
        
        # Check rate limit
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        
        # Update tracking
        self._last_request_time = time.time()
        self._request_times.append(self._last_request_time)

    async def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Make an async request to the SEC API with proper headers and rate limiting.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            
        Returns:
            str: Response text from the SEC API
            
        Raises:
            aiohttp.ClientError: If the request fails
        """
        await self._wait_for_rate_limit()
        
        headers = headers or self.headers
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.text()

    async def _make_json_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict:
        """Make an async request to the SEC API and parse JSON response with rate limiting.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            
        Returns:
            Dict: Parsed JSON response
            
        Raises:
            aiohttp.ClientError: If the request fails
            ValueError: If the response is not valid JSON
        """
        await self._wait_for_rate_limit()
            
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
    
    async def get_latest_filings(self, limit: int = 40, filing_type: str = '8-K') -> pd.DataFrame:
        """Retrieves the latest filings from the SEC.
        
        Args:
            limit: Maximum number of filings to return (default: 40)
            filing_type: Type of filing to retrieve (default: '8-K')
            
        Returns:
            DataFrame containing filing information
        """
        url = f"{self.client.base_url}/cgi-bin/browse-edgar?company=&CIK=&type={filing_type}&owner=include&count={limit}&action=getcurrent&output=atom"
        resp = await self.client._make_request(url, self.client.headers)
        df = parse_atom_latest_filings_feed(resp)
        filtered_df = filter_8k_feed_by_items(df)

        # Get URLs and text content
        extracted_urls = await asyncio.gather(*[
            self._get_8k_urls(url) for url in filtered_df['base_url']
        ])
        filtered_df[['url_8k', 'url_ex99']] = pd.DataFrame([
            url.model_dump() for url in extracted_urls
        ])[['url_8k', 'url_ex99']]

        filtered_df['url_text'] = await asyncio.gather(*[
            self._get_url_text(url) for url in filtered_df['url_8k']
        ])
        return filtered_df

    async def _get_8k_urls(self, base_url: str) -> ExtractedUrls:
        """Get 8-K URLs from base URL.
        
        Args:
            base_url: Base URL to extract from
            
        Returns:
            ExtractedUrls object containing URLs
        """
        html = await self.client._make_request(base_url, self.client.headers)
        return extract_8k_url_from_base_url(html)

    async def _get_url_text(self, url: str) -> str:
        """Get text content from URL.
        
        Args:
            url: URL to get text from
            
        Returns:
            str: Text content
        """
        html = await self.client._make_request(url, self.client.headers)
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()

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

        html = await self.client._make_request(root_url, self.client.headers)
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
