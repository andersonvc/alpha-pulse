import asyncio
import logging
from typing import Optional
import pandas as pd
import json

from alpha_pulse.tools.edgar import EdgarAPI
from alpha_pulse.db import DuckDBManager
from alpha_pulse.types.edgar8k import State8K
from alpha_pulse.graphs.edgar_8k_workflow import run_workflow

async def check_record_exists(db_manager: DuckDBManager, cik: str, filing_date: str, item_number: str) -> bool:
    """Check if a record exists in the database.
    
    Args:
        db_manager: Database manager instance
        cik: Company CIK
        filing_date: Filing date
        item_number: Item number
        
    Returns:
        bool: True if record exists, False otherwise
    """
    # Determine which table to check based on item number
    table_name = "items_8k_502" if item_number == "5.02" else "items_8k_801"
    
    query = f'''
        SELECT 1
        FROM {table_name}
        WHERE cik = '{cik}' 
        AND filing_date = '{filing_date}' 
        AND item_number = '{item_number}'
        LIMIT 1
    '''
    result = db_manager.conn.execute(query).fetchone()
    return result is not None

async def check_raw_8k_record_exists(db_manager: DuckDBManager, url_8k: str) -> bool:
    """Check if a record exists in the raw_8k_data table.
    
    Args:
        db_manager: Database manager instance
        url_8k: URL of the 8-K filing
        
    Returns:
        bool: True if record exists, False otherwise
    """
    if not url_8k:
        return False
        
    query = f'''
        SELECT 1
        FROM raw_8k_data
        WHERE url_8k = '{url_8k}'
        LIMIT 1
    '''
    result = db_manager.conn.execute(query).fetchone()
    return result is not None

async def process_new_filings(limit: int = 40) -> None:
    """Process new 8-K filings and store them in the database.
    
    Args:
        limit: Maximum number of filings to process
    """
    # Get latest filings
    df = await EdgarAPI().get_latest_filings(limit=limit)
    df = df.rename(columns={'date': 'filing_date'})
    df = df[df['filtered_items'].isin(['5.02','8.01'])]
    
    # Process each filing
    async with DuckDBManager(db_path="data/alpha_pulse.db") as db_manager:
        for _, row in df.iterrows():
            # Create State8K object
            state = State8K(
                cik=row['cik'],
                filing_date=row['filing_date'],
                raw_text=row['url_text'],
                items=row['filtered_items'],
                url_8k=row.get('url_8k', ''),  # Ensure url_8k is set
                url_ex99=row.get('url_ex99', '')  # Ensure url_ex99 is set
            )

            # check if record exists in duckdb table titled 'raw_8k_data'
            if await check_raw_8k_record_exists(db_manager, state.url_8k):
                logging.info(f"Record already exists: {state.cik} - {state.filing_date} - {state.items}")
                continue
            # write raw state to duckdb table titled 'raw_8k_data'
            db_manager.insert_raw_8k_data(state)
            
            # Run workflow
            result = await run_workflow(state)

            if result is not None:
                result_df = pd.DataFrame([v.model_dump() for v in result.parsed_items.values()])
                db_manager.insert_8k_items(result_df, item_type=result_df['item_number'].values[0])
                logging.info(f"Inserted new record: {row['cik']} - {row['filing_date']} - {row['filtered_items']}")

def print_all_filings() -> None:
    """Print all filings from the database."""
    with DuckDBManager(db_path="data/alpha_pulse.db") as db_manager:
        df = db_manager.get_all_filings()
        print(df)

async def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    await process_new_filings(limit=200)
    print_all_filings()

if __name__ == "__main__":
    asyncio.run(main())