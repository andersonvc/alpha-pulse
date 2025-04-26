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
    
    # Convert to DataFrame and ensure all required columns are present
    result_df = pd.DataFrame([v.model_dump() for v in result.parsed_items.values()])
    print(result_df)
    raise Exception("Stop here")
    
    # Convert individuals to JSON string if present
    if 'individuals' in result_df.columns:
        result_df['individuals'] = result_df['individuals'].apply(lambda x: json.dumps(x) if x else "[]")
    
    # Add any missing columns with default values
    if first_item == "5.02":
        required_columns = db_manager._get_model_fields(db_manager.ITEMS_8K_502.model)
    else:
        required_columns = db_manager._get_model_fields(db_manager.ITEMS_8K_801.model)
    
    # Ensure required fields have valid values
    for col in required_columns:
        if col not in result_df.columns:
            if col in ['cik', 'filing_date', 'item_number']:
                result_df[col] = row[col] if col != 'item_number' else first_item
            else:
                result_df[col] = ""
    
    # Debug logging
    #logging.info(f"DataFrame columns: {result_df.columns.tolist()}")
    #logging.info(f"DataFrame shape: {result_df.shape}")
    #logging.info(f"CIK values: {result_df['cik'].tolist()}")
    #logging.info(f"Filing date values: {result_df['filing_date'].tolist()}")
    #logging.info(f"Item number values: {result_df['item_number'].tolist()}")
    
    # Insert into appropriate table based on item type
    if first_item == "5.02":
        db_manager.insert_8k_items(result_df, item_type="502")
    else:
        db_manager.insert_8k_items(result_df, item_type="801")
        
    return result_df

async def process_new_filings(limit: int = 40) -> None:
    """Process new 8-K filings and store them in the database.
    
    Args:
        limit: Maximum number of filings to process
    """
    # Get latest filings
    df = await EdgarAPI().get_latest_filings(limit=limit)
    df = df.rename(columns={'date': 'filing_date'})
    df = df[df['filtered_items'].isin(['5.02','8.01'])]
    df = df.head(5)
    print(df)
    
    # Initialize database manager
    db_manager = DuckDBManager(db_path="data/alpha_pulse.db")
    
    # Process each filing
    for _, row in df.iterrows():
        # Create State8K object
        state = State8K(
            cik=row['cik'],
            filing_date=row['filing_date'],
            raw_text=row['url_text'],
            items=row['filtered_items']
        )
        
        # Run workflow
        result = await run_workflow(state)


        if result is not None:
            result_df = pd.DataFrame([v.model_dump() for v in result.parsed_items.values()])
            print("NNNNNNNNNNNNNNNNNNNNNNNNNN")
            print(result_df['item_number'])
            print("MMMMMMMMMMMMMMMMMMMMMMMMMM")
            print(row['filtered_items'])
            print("LLLLLLLLLLLLLLLLLLLLLLLLLL")
            db_manager.insert_8k_items(result_df, item_type=result_df['item_number'].values[0])
            logging.info(f"Inserted new record: {row['cik']} - {row['filing_date']} - {row['filtered_items']}")

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