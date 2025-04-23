import asyncio
import logging
#from alpha_pulse.agents.edgar_8k_agent import Edgar8kAgent
#from alpha_pulse.agents.edgar.agent_8k_parser import create_8k_parser_graph
from alpha_pulse.tools.edgar import EdgarAPI
from alpha_pulse.db import DuckDBManager
import pandas as pd
from alpha_pulse.types.simple8k import SimpleState8K
from alpha_pulse.graphs.simple8k_graph import run_workflow

async def check_record_exists(db_manager: DuckDBManager, cik: str, filing_date: str, item_number: str) -> bool:
    """Check if a record exists in the database."""
    query = f'''
        SELECT 1
        FROM simple8k_items_801
        WHERE cik = '{cik}' 
        AND filing_date = '{filing_date}' 
        AND item_number = '{item_number}'
        LIMIT 1
    '''
    result = db_manager.conn.execute(query).fetchone()
    return result is not None

async def process_new_filings():
    """Process new 8-K filings and store them in the database."""
    # Get latest filings
    df = await EdgarAPI().get_latest_filings()

    df = df.rename(columns={'date': 'filing_date'})
    
    df = df[df['filtered_items']=='8.01']
    
    # Initialize database manager
    db_manager = DuckDBManager(db_path="data/alpha_pulse.db")
    
    # Process each filing
    for _, row in df.iterrows():

        cik = row['cik']
        filing_date = row['filing_date']
        filtered_items = row['filtered_items']
        raw_text = row['url_text']

        first_item = filtered_items.split(',')[0]

        # Check if record exists - if any of the items are already processed, skip
        if await check_record_exists(db_manager, cik, filing_date, first_item):
            print(f"Skipping existing record: {cik} - {filing_date} - {first_item}")
            continue
        
        # Convert to SimpleState8K
        state = SimpleState8K(
            cik=cik,
            filing_date=filing_date,
            raw_text=raw_text,
            items=filtered_items,
        )
        
        # Process filing
        result = await run_workflow(state)
        
        # Create DataFrame from parsed items
        result_df = pd.DataFrame([v.model_dump() for v in result.parsed_items.values()])
        
        # Insert into database
        db_manager.insert_simple8k_items(result_df)
        print(f"Inserted new record: {row['cik']} - {row['filing_date']}")

def print_all_filings():
    db_manager = DuckDBManager(db_path="data/alpha_pulse.db")
    df = db_manager.get_all_filings()
    print(df)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(process_new_filings())
    print_all_filings()