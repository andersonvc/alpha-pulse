"""Tests for the SEC EDGAR API client.

This module contains tests for the SECClient class, which handles making requests
to the SEC EDGAR API with proper rate limiting and error handling.
"""

import pytest
import aiohttp
from unittest.mock import patch, AsyncMock, MagicMock
from alpha_pulse.tools.edgar.sec_client import SECClient, SEC_BASE_URL, SEC_API_BASE_URL

# Test URLs
TEST_URL = "https://example.com"
TEST_API_URL = f"{SEC_API_BASE_URL}/test"
TEST_8K_URL = f"{SEC_BASE_URL}/test"

@pytest.fixture
def mock_aiohttp_session():
    """Fixture to mock aiohttp.ClientSession and session.get.
    
    This fixture sets up the necessary mocks for testing aiohttp's async context
    managers and response handling.
    
    Returns:
        dict: Dictionary containing all the mock objects needed for testing
    """
    with patch('aiohttp.ClientSession') as mock_session_class:
        # Mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__aenter__.return_value = mock_session

        # Prepare a mock for the response context manager
        mock_response_cm = MagicMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = AsyncMock()
        mock_response.json = AsyncMock()
        mock_response_cm.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_response_cm

        yield {
            'mock_session_class': mock_session_class,
            'mock_session': mock_session,
            'mock_response': mock_response,
            'mock_response_cm': mock_response_cm
        }

@pytest.fixture
def sec_client():
    """Create a SECClient instance for testing."""
    return SECClient()

@pytest.mark.asyncio
class TestSECClient:
    """Test suite for SECClient class."""
    
    async def test_make_request_success(self, sec_client, mock_aiohttp_session):
        """Test successful request to SEC API."""
        expected_response = "Test response"
        
        # Set what the mock response should return
        mock_aiohttp_session['mock_response'].text.return_value = expected_response
        
        # Make the request
        response = await sec_client._make_request(TEST_URL)
        
        # Verify the response
        assert response == expected_response
        
        # Verify the request was made with correct parameters
        mock_aiohttp_session['mock_session'].get.assert_called_once_with(
            TEST_URL, 
            headers=sec_client.headers
        )

    async def test_make_request_error(self, sec_client, mock_aiohttp_session):
        """Test request error handling."""
        # Simulate session.get raising ClientError on __aenter__
        mock_aiohttp_session['mock_response_cm'].__aenter__.side_effect = \
            aiohttp.ClientError("Test error")

        # Verify the error is raised
        with patch.object(sec_client._rate_limiter, 'wait', new_callable=AsyncMock) as mock_wait:
            with pytest.raises(aiohttp.ClientError) as exc_info:
                await sec_client._make_request(TEST_8K_URL)
            
            assert str(exc_info.value) == "Test error"
            mock_wait.assert_called_once()

    async def test_make_json_request_success(self, sec_client, mock_aiohttp_session):
        """Test successful JSON request to SEC API."""
        expected_response = {"test": "data"}
        
        # Set mock .json() to return expected_response
        mock_aiohttp_session['mock_response'].json.return_value = expected_response

        # Make the request
        with patch.object(sec_client._rate_limiter, 'wait', new_callable=AsyncMock) as mock_wait:
            response = await sec_client._make_json_request(TEST_API_URL)
            
            # Verify the response
            assert response == expected_response
            mock_wait.assert_called_once()
            
            # Verify the request was made with correct parameters
            mock_aiohttp_session['mock_session'].get.assert_called_once_with(
                TEST_API_URL,
                headers=sec_client.headers
            )

    async def test_make_json_request_invalid_json(self, sec_client, mock_aiohttp_session):
        """Test handling of invalid JSON response."""
        # Simulate .json() raising a ValueError
        mock_aiohttp_session['mock_response'].json.side_effect = ValueError("Invalid JSON")

        # Verify the error is raised
        with patch.object(sec_client._rate_limiter, 'wait', new_callable=AsyncMock) as mock_wait:
            with pytest.raises(ValueError) as exc_info:
                await sec_client._make_json_request(TEST_API_URL)
            
            assert str(exc_info.value) == "Invalid JSON"
            mock_wait.assert_called_once()

    async def test_custom_headers(self, sec_client, mock_aiohttp_session):
        """Test request with custom headers."""
        custom_headers = {"X-Test": "test-value"}
        
        # Mock text() to return dummy text
        mock_aiohttp_session['mock_response'].text.return_value = "Test response"

        # Make the request with custom headers
        with patch.object(sec_client._rate_limiter, 'wait', new_callable=AsyncMock) as mock_wait:
            await sec_client._make_request(TEST_8K_URL, headers=custom_headers)
            
            # Verify the request was made with custom headers
            mock_aiohttp_session['mock_session'].get.assert_called_once_with(
                TEST_8K_URL,
                headers=custom_headers
            )