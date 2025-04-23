import asyncio
import logging
from typing import Optional
import pandas as pd

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
    query = f'''
        SELECT 1
        FROM items_8k_801
        WHERE cik = '{cik}' 
        AND filing_date = '{filing_date}' 
        AND item_number = '{item_number}'
        LIMIT 1
    '''
    result = db_manager.conn.execute(query).fetchone()
    return result is not None

async def process_filing(db_manager: DuckDBManager, row: pd.Series) -> Optional[pd.DataFrame]:
    """Process a single 8-K filing.
    
    Args:
        db_manager: Database manager instance
        row: DataFrame row containing filing data
        
    Returns:
        Optional[pd.DataFrame]: Processed filing data if successful, None if skipped
    """
    cik = row['cik']
    filing_date = row['filing_date']
    filtered_items = row['filtered_items']
    raw_text = row['url_text']
    first_item = filtered_items.split(',')[0]

    # Check if record exists
    if await check_record_exists(db_manager, cik, filing_date, first_item):
        logging.info(f"Skipping existing record: {cik} - {filing_date} - {first_item}")
        return None

    # Process filing
    state = State8K(
        cik=cik,
        filing_date=filing_date,
        raw_text=raw_text,
        items=filtered_items,
    )
    
    result = await run_workflow(state)
    return pd.DataFrame([v.model_dump() for v in result.parsed_items.values()])

async def process_new_filings(limit: int = 40) -> None:
    """Process new 8-K filings and store them in the database.
    
    Args:
        limit: Maximum number of filings to process
    """
    # Get latest filings
    df = await EdgarAPI().get_latest_filings(limit=limit)
    df = df.rename(columns={'date': 'filing_date'})
    df = df[df['filtered_items']=='8.01']
    
    # Initialize database manager
    db_manager = DuckDBManager(db_path="data/alpha_pulse.db")
    
    # Process each filing
    for _, row in df.iterrows():
        result_df = await process_filing(db_manager, row)
        if result_df is not None:
            db_manager.insert_8k_items(result_df)
            logging.info(f"Inserted new record: {row['cik']} - {row['filing_date']}")

def print_all_filings() -> None:
    """Print all filings from the database."""
    db_manager = DuckDBManager(db_path="data/alpha_pulse.db")
    df = db_manager.get_all_filings()
    print(df)

async def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    await process_new_filings()
    print_all_filings()

if __name__ == "__main__":
    asyncio.run(main())