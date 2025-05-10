"""SEC EDGAR API client for making rate-limited requests."""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import aiohttp
from aiohttp import ClientError
import fitz
from alpha_pulse.clients.sec.rate_limiter import RateLimiter

# Constants
SEC_BASE_URL = "https://www.sec.gov"
SEC_API_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    "User-Agent": os.getenv("USER_AGENT", "Mozilla/5.0"),
    "Accept-Encoding": "gzip, deflate",
}

@dataclass
class SECClient:
    """Client for interacting with SEC EDGAR API.
    
    This client handles making requests to the SEC EDGAR API with proper rate limiting
    and error handling. It uses a singleton RateLimiter to ensure all requests across
    the application respect SEC's rate limits.
    
    Attributes:
        base_url: Base URL for SEC website
        api_base_url: Base URL for SEC API
        headers: HTTP headers for SEC requests
        _rate_limiter: Rate limiter instance for managing request timing
    """
    
    base_url: str = SEC_BASE_URL
    api_base_url: str = SEC_API_BASE_URL
    headers: Dict[str, str] = field(default_factory=lambda: SEC_HEADERS.copy())
    _rate_limiter: RateLimiter = field(default_factory=RateLimiter)

    async def _make_request(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        raise_for_status: bool = True
    ) -> str:
        """Make an async request to the SEC API with proper headers and rate limiting.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            raise_for_status: Whether to raise an exception for non-200 status codes
            
        Returns:
            str: Response text from the SEC API
            
        Raises:
            ClientError: If the request fails
            ValueError: If the response status code indicates an error
        """
        logging.info(f"Making request to {url}")
        await self._rate_limiter.wait()
        
        headers = headers or self.headers
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if raise_for_status:
                        response.raise_for_status()
                    return await response.text()
        except ClientError as e:
            logging.error(f"Request failed: {str(e)}")
            raise

    async def _make_json_request(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        raise_for_status: bool = True
    ) -> Dict[str, Any]:
        """Make an async request to the SEC API and parse JSON response with rate limiting.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            raise_for_status: Whether to raise an exception for non-200 status codes
            
        Returns:
            Dict[str, Any]: Parsed JSON response
            
        Raises:
            ClientError: If the request fails
            ValueError: If the response is not valid JSON or status code indicates an error
        """
        logging.info(f"Making JSON request to {url}")
        await self._rate_limiter.wait()
            
        headers = headers or self.headers
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if raise_for_status:
                        response.raise_for_status()
                    return await response.json()
        except ClientError as e:
            logging.error(f"Request failed: {str(e)}")
            raise
        except ValueError as e:
            logging.error(f"Invalid JSON response: {str(e)}")
            raise

    async def _make_pdf_request(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        raise_for_status: bool = True
    ) -> str:
        """Make an async request to the SEC API with proper headers and rate limiting.
        
        Args:
            url: URL to request
            headers: Optional custom headers
            raise_for_status: Whether to raise an exception for non-200 status codes
            
        Returns:
            str: Response text from the SEC API
            
        Raises:
            ClientError: If the request fails
            ValueError: If the response status code indicates an error
        """
        logging.info(f"Making request to {url}")
        await self._rate_limiter.wait()
        
        headers = headers or self.headers
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if raise_for_status:
                        response.raise_for_status()
                    pdf_bytes = await response.content.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    return text
        except ClientError as e:
            logging.error(f"Request failed: {str(e)}")
            raise