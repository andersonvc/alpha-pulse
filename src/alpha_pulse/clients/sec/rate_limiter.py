"""Rate limiter for SEC EDGAR API requests.

This module provides a thread-safe rate limiter that enforces SEC's rate limits:
- 10 requests per second
- Burst limit of 8 requests in a 1-second window
"""

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import List
from threading import Lock

# Constants
SEC_RATE_LIMIT = 0.12  # 8 requests per second (more conservative than SEC's 10)
SEC_BURST_LIMIT = 8    # Maximum number of requests in a burst
SEC_BURST_WINDOW = 1.0 # Time window for burst limit in seconds

@dataclass
class RateLimiter:
    """Thread-safe rate limiter for SEC requests.
    
    This class implements a rate limiter that enforces SEC's rate limits across
    all requests in the application. It uses a singleton pattern to ensure all
    requests share the same rate limiting state.
    
    The rate limiter enforces:
    - A maximum of 8 requests per second (more conservative than SEC's 10)
    - A burst limit of 8 requests in a 1-second window
    
    Attributes:
        last_request_time: Timestamp of the last request
        request_times: List of timestamps for requests in the current burst window
    """
    _instance = None
    _lock = Lock()
    _async_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    last_request_time: float = field(default=0.0)
    request_times: List[float] = field(default_factory=list)
    
    def __new__(cls):
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.last_request_time = 0.0
                cls._instance.request_times = []
                cls._instance._async_lock = asyncio.Lock()
            return cls._instance
    
    async def wait(self) -> None:
        """Wait if necessary to respect rate limits.
        
        This method:
        1. Cleans up old request times
        2. Checks burst limit and waits if necessary
        3. Checks rate limit and waits if necessary
        4. Updates request tracking
        
        The method is thread-safe and can be called concurrently.
        """
        async with self._async_lock:
            now = time.time()
            
            # Clean up old request times
            self.request_times = [t for t in self.request_times if now - t < SEC_BURST_WINDOW]
            
            # Check burst limit
            if len(self.request_times) >= SEC_BURST_LIMIT:
                # Wait until the oldest request is outside the burst window
                wait_time = self.request_times[0] + SEC_BURST_WINDOW - now
                if wait_time > 0:
                    logging.info(f"Burst limit reached. Waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Update now after waiting
                    now = time.time()
                    # Clean up old request times again after waiting
                    self.request_times = [t for t in self.request_times if now - t < SEC_BURST_WINDOW]
            
            # Check rate limit
            if self.last_request_time > 0:  # Skip for first request
                elapsed = now - self.last_request_time
                if elapsed < SEC_RATE_LIMIT:
                    wait_time = SEC_RATE_LIMIT - elapsed
                    logging.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Update now after waiting
                    now = time.time()
            
            # Update tracking
            self.last_request_time = now
            self.request_times.append(now)
            
            # Log current state
            logging.debug(
                f"Rate limiter state: {len(self.request_times)} requests in last "
                f"{SEC_BURST_WINDOW} seconds"
            )
