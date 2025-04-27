"""Tests for the SEC EDGAR rate limiter."""

import asyncio
import time
import pytest
from alpha_pulse.tools.edgar.rate_limiter import RateLimiter, SEC_RATE_LIMIT, SEC_BURST_LIMIT, SEC_BURST_WINDOW
import logging

@pytest.mark.asyncio
async def test_rate_limit_not_exceeded():
    """Test that the rate limiter enforces the SEC rate limit."""
    limiter = RateLimiter()
    start_time = time.time()
    
    # Make multiple requests in quick succession
    for _ in range(10):
        await limiter.wait()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Calculate the minimum expected time based on rate limit
    min_expected_time = (10 - 1) * SEC_RATE_LIMIT  # 9 intervals between 10 requests
    
    # Verify that we didn't exceed the rate limit
    assert elapsed >= min_expected_time, (
        f"Rate limit exceeded. Elapsed time: {elapsed:.2f}s, "
        f"Minimum expected time: {min_expected_time:.2f}s"
    )

@pytest.mark.asyncio
async def test_burst_limit_not_exceeded():
    """Test that the rate limiter enforces the burst limit."""
    limiter = RateLimiter()
    start_time = time.time()
    
    # Make more requests than the burst limit
    for _ in range(SEC_BURST_LIMIT + 5):
        await limiter.wait()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Calculate the minimum expected time based on burst limit
    min_expected_time = (SEC_BURST_LIMIT + 5 - 1) * SEC_RATE_LIMIT
    
    # Verify that we didn't exceed the burst limit
    assert elapsed >= min_expected_time, (
        f"Burst limit exceeded. Elapsed time: {elapsed:.2f}s, "
        f"Minimum expected time: {min_expected_time:.2f}s"
    )

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test that the rate limiter handles concurrent requests correctly."""
    limiter = RateLimiter()
    start_time = time.time()
    
    # Create multiple concurrent requests
    async def make_request():
        await limiter.wait()
        return time.time()  # Return the time when the request was processed
    
    # Launch multiple requests concurrently
    tasks = [make_request() for _ in range(10)]
    request_times = await asyncio.gather(*tasks)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Sort request times to analyze the sequence
    request_times.sort()
    
    # Calculate intervals between consecutive requests
    intervals = [request_times[i] - request_times[i-1] for i in range(1, len(request_times))]
    
    # Verify that no interval is shorter than the rate limit
    for i, interval in enumerate(intervals):
        assert interval >= SEC_RATE_LIMIT, (
            f"Rate limit exceeded between requests {i} and {i+1}. "
            f"Interval: {interval:.2f}s, Minimum expected: {SEC_RATE_LIMIT:.2f}s"
        )
    
    # Verify that we don't exceed the burst limit
    for i in range(len(request_times) - SEC_BURST_LIMIT):
        burst_window = request_times[i + SEC_BURST_LIMIT] - request_times[i]
        assert burst_window >= SEC_BURST_WINDOW, (
            f"Burst limit exceeded in window starting at request {i}. "
            f"Window duration: {burst_window:.2f}s, Minimum expected: {SEC_BURST_WINDOW:.2f}s"
        )
    
    # Log the results for debugging
    logging.info(f"Total elapsed time: {elapsed:.2f}s")
    logging.info(f"Request intervals: {[f'{i:.2f}s' for i in intervals]}")
    logging.info(f"Average interval: {sum(intervals)/len(intervals):.2f}s")

@pytest.mark.asyncio
async def test_singleton_behavior():
    """Test that the rate limiter maintains singleton behavior."""
    limiter1 = RateLimiter()
    limiter2 = RateLimiter()
    
    # Verify that both instances are the same object
    assert limiter1 is limiter2, "Rate limiter is not maintaining singleton behavior"
    
    # Verify that state is shared between instances
    await limiter1.wait()
    start_time = time.time()
    await limiter2.wait()
    elapsed = time.time() - start_time
    
    # The second request should respect the rate limit
    assert elapsed >= SEC_RATE_LIMIT, (
        f"Rate limit not respected between singleton instances. "
        f"Elapsed time: {elapsed:.2f}s, Minimum expected time: {SEC_RATE_LIMIT:.2f}s"
    ) 