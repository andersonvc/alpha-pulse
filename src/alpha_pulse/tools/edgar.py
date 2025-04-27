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
