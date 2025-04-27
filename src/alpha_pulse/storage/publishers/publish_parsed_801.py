import os
import pandas as pd
import asyncio
import duckdb
from pydantic import ValidationError
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
from alpha_pulse.types.dbtables.analyzed_801_text import Analyzed801Text
import warnings

async def publish_parsed_801(record: Parsed8KText):
    db_path = os.getenv('DUCKDB_PATH')
    if not db_path:
        raise ValueError("DUCKDB_PATH environment variable not set.")

    def insert(record: Analyzed801Text):

        con = duckdb.connect(database=db_path, read_only=False)

        try:
            # --- Create tables ---
            con.execute("""
            CREATE TABLE IF NOT EXISTS analyzed_item801 (
                category TEXT,
                summary_list TEXT,
                sentiment TEXT,
                price_impact TEXT,
                is_event_unexpected BOOLEAN,
                cik TEXT,
                filing_date DATE,
                item_number TEXT,
                base_url TEXT,
                ts TIMESTAMP
            )""")


            # --- Validate input ---
            try:
                analyzed_item = Analyzed801Text(**record.model_dump())
            except ValidationError as e:
                print(f"Validation error: {e}")
                raise

            # --- Check if summary already exists ---
            existing_cik = con.execute("""
                SELECT cik FROM analyzed_item801 
                WHERE cik = ? AND filing_date = ? AND item_number = ?
            """, [record.cik, record.filing_date, record.item_number]).fetchone()

            if existing_cik:
                con.execute("DELETE FROM analyzed_item801 WHERE cik = ? AND filing_date = ? AND item_number = ?", [record.cik, record.filing_date, record.item_number])

            # --- Insert or update summary ---
            analyzed_row = analyzed_item.to_db_dict()
            analyzed_df = pd.DataFrame([analyzed_row])

            if existing_cik:
                # Update
                con.execute("""
                    UPDATE analyzed_item801 SET 
                        category = ?, summary_list = ?, sentiment = ?, price_impact = ?, is_event_unexpected = ?, ts = ?
                    WHERE cik = ? AND filing_date = ? AND item_number = ?
                """, [analyzed_row['category'], analyzed_row['summary_list'], analyzed_row['sentiment'], analyzed_row['price_impact'], analyzed_row['is_event_unexpected'], analyzed_row['ts'], record.cik, record.filing_date, record.item_number])
            else:
                # Insert
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    analyzed_df.to_sql('analyzed_item801', con=con, if_exists='append', index=False)

        finally:
            con.close()

    await asyncio.to_thread(insert, record)
