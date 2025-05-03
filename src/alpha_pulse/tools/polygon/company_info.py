"""Polygon.io API client for company information.

This module provides functions to interact with Polygon.io's API to fetch and update
company information such as tickers, market caps, and SIC codes.
"""

import os
import aiohttp
from typing import Optional, Tuple, List, Dict
from alpha_pulse.storage.base_db_client import DuckDBClient
from alpha_pulse.storage.edgar_db_client import EdgarDBClient
import asyncio

# API Constants
POLYGON_BASE_URL = "https://api.polygon.io/v3/reference"
API_KEY = os.getenv('POLYGON_API_KEY')

async def get_ticker_by_cik(cik: str) -> str:
    """Get a company's ticker symbol from its CIK.
    
    Args:
        cik: The company's CIK identifier
        
    Returns:
        The company's ticker symbol, or empty string if not found
    """
    url = f"{POLYGON_BASE_URL}/tickers"
    params = {
        "cik": cik,
        "active": "true",
        "limit": 1,
        "apiKey": API_KEY
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            results = data.get("results", [])
            if not results:
                return ''
            return results[0]["ticker"]

async def get_market_cap_by_ticker(ticker: str) -> float:
    """Get a company's market cap from its ticker.
    
    Args:
        ticker: The company's ticker symbol
        
    Returns:
        The company's market cap in billions USD, or 0.0 if not found
    """
    try:
        url = f"{POLYGON_BASE_URL}/tickers/{ticker}"
        params = {"apiKey": API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data["results"]["market_cap"] * 1e-9
    except:
        return 0.0

async def get_sic_by_ticker(ticker: str) -> str:
    """Get a company's SIC code from its ticker.
    
    Args:
        ticker: The company's ticker symbol
        
    Returns:
        The company's SIC code, or empty string if not found
    """
    try:
        url = f"{POLYGON_BASE_URL}/tickers/{ticker}"
        params = {"apiKey": API_KEY}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data["results"]["sic_code"]
    except:
        return ""

async def get_company_info(cik: str) -> Dict[str, str | float]:
    """Get all company information from Polygon.io.
    
    Args:
        cik: The company's CIK identifier
        
    Returns:
        Dictionary containing company information:
        {
            'cik': str,
            'ticker': str,
            'market_cap': float,
            'sic': str
        }
    """
    # First get the ticker
    ticker = await get_ticker_by_cik(cik)
    if not ticker:
        return {
            'cik': cik,
            'ticker': '',
            'market_cap': 0.0,
            'sic': ''
        }
        
    # Then get market cap and SIC
    market_cap = await get_market_cap_by_ticker(ticker)
    sic = await get_sic_by_ticker(ticker)
    
    return {
        'cik': cik,
        'ticker': ticker,
        'market_cap': market_cap,
        'sic': sic
    }

def update_company_info(db: DuckDBClient, company_info: Dict[str, str | float]) -> None:
    """Update company information in the database.
    
    Args:
        db: Database client
        company_info: Dictionary containing company information
    """
    query = """
        UPDATE filed_8k_listing 
        SET ticker = ?, market_cap = ?, sic = ?
        WHERE cik = ?
    """
    db.execute(query, (
        company_info['ticker'],
        company_info['market_cap'],
        company_info['sic'],
        company_info['cik']
    ))

async def get_batch_company_info(ciks: List[str]) -> List[Dict[str, str | float]]:
    """Get company information for a batch of CIKs.
    
    Args:
        ciks: List of CIKs to get information for
        
    Returns:
        List of dictionaries containing company information
    """
    tasks = [get_company_info(cik) for cik in ciks]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out any errors and return successful results
    return [
        result for result in results 
        if not isinstance(result, Exception)
    ]

def update_batch_company_info(db: DuckDBClient, company_infos: List[Dict[str, str | float]]) -> None:
    """Update company information for a batch of companies.
    
    Args:
        db: Database client
        company_infos: List of dictionaries containing company information
    """
    for company_info in company_infos:
        try:
            update_company_info(db, company_info)
            print(f"Updated company info for CIK: {company_info['cik']}")
        except Exception as e:
            print(f"Error updating company info for CIK {company_info['cik']}: {str(e)}")
            continue

async def update_all_company_info(batch_size: int = 100) -> None:
    """Update company information for all records in filed_8k_listing.
    
    This function:
    1. Gets all unique CIKs from filed_8k_listing
    2. Processes them in batches to avoid rate limiting
    3. Updates each record with company information
    
    Args:
        batch_size: Number of records to process in each batch
    """
    # Initialize the database client
    db = EdgarDBClient()
    db._startup_db()
    
    try:
        # Get all unique CIKs
        query = "SELECT DISTINCT cik FROM filed_8k_listing"
        results = db.fetchall_dict(query)
        ciks = [row['cik'] for row in results]
        
        # Process in batches
        for i in range(0, len(ciks), batch_size):
            batch = ciks[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} of {(len(ciks) + batch_size - 1)//batch_size}")
            
            # Get company info for the batch
            company_infos = await get_batch_company_info(batch)
            
            # Update database with the batch
            update_batch_company_info(db, company_infos)
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(update_all_company_info())