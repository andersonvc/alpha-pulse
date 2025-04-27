import os
import pandas as pd
import asyncio
import duckdb
from typing import List
from pydantic import ValidationError
from alpha_pulse.types.dbtables.parsed_items import Item502Summary, RoleChange
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
import warnings

async def publish_parsed_502(source_item: Parsed8KText, item_summary: Item502Summary):
    db_path = os.getenv('DUCKDB_PATH')
    if not db_path:
        raise ValueError("DUCKDB_PATH environment variable not set.")

    def insert(source_item: Parsed8KText, item_summary: Item502Summary):

        con = duckdb.connect(database=db_path, read_only=False)

        try:
            # --- Create tables ---
            con.execute("""
            CREATE TABLE IF NOT EXISTS item502_summary (
                category TEXT,
                filing_date DATE,
                cik TEXT,
                base_url TEXT,
                item_number TEXT,
                ts TIMESTAMP
            )""")

            con.execute("""
            CREATE TABLE IF NOT EXISTS item502_appointment (
                cik TEXT,
                filing_date DATE,
                name TEXT,
                role TEXT,
                effective_date TEXT
            )""")

            con.execute("""
            CREATE TABLE IF NOT EXISTS item502_removal (
                cik TEXT,
                filing_date DATE,
                summary_id BIGINT,
                name TEXT,
                role TEXT,
                effective_date TEXT
            )""")

            # --- Validate input ---
            try:
                item_summary = Item502Summary(**item_summary.model_dump())
            except ValidationError as e:
                print(f"Validation error: {e}")
                raise

            # --- Check if summary already exists ---
            existing_cik = con.execute("""
                SELECT cik FROM item502_summary 
                WHERE cik = ? AND filing_date = ?
            """, [source_item.cik, source_item.filing_date]).fetchone()

            if existing_cik:
                con.execute("DELETE FROM item502_appointment WHERE cik = ? AND filing_date = ?", [source_item.cik, source_item.filing_date])
                con.execute("DELETE FROM item502_removal WHERE cik = ? AND filing_date = ?", [source_item.cik, source_item.filing_date])

            # --- Insert or update summary ---
            summary_row = item_summary.to_db_dict(source_item)
            summary_df = pd.DataFrame([summary_row])

            if existing_cik:
                # Update
                con.execute("""
                    UPDATE item502_summary SET 
                        category = ?, base_url = ?, item_number = ?, ts = ?
                    WHERE cik = ? AND filing_date = ?
                """, [summary_row['category'], summary_row['base_url'], summary_row['item_number'], summary_row['ts'], source_item.cik, source_item.filing_date])
            else:
                # Insert
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    summary_df.to_sql('item502_summary', con=con, if_exists='append', index=False)

            # --- Insert Role Changes ---
            def insert_rolechanges(role_list: List[RoleChange], table_name: str):
                if not role_list:
                    return
                role_df = pd.DataFrame([r.to_db_dict(source_item) for r in role_list])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=UserWarning)
                    role_df.to_sql(table_name, con=con, if_exists='append', index=False)

            insert_rolechanges(item_summary.appointment, "item502_appointment")
            insert_rolechanges(item_summary.removal, "item502_removal")

        finally:
            con.close()

    await asyncio.to_thread(insert, source_item, item_summary)

# --- Optional View Creation ---
def create_combined_view():
    db_path = os.getenv('DUCKDB_PATH')
    if not db_path:
        raise ValueError("DUCKDB_PATH environment variable not set.")

    con = duckdb.connect(database=db_path, read_only=False)

    try:
        view_name = "parsed_item502"
        con.execute(f"""
            CREATE OR REPLACE VIEW {view_name} AS
            SELECT 
                s.category,
                s.filing_date,
                s.cik,
                s.base_url,
                s.item_number,
                s.ts,
                'appointment' AS event_type,
                a.name,
                a.role,
                a.effective_date
            FROM item502_summary s
            INNER JOIN item502_appointment a ON s.cik = a.cik AND s.filing_date = a.filing_date

            UNION ALL

            SELECT 
                s.category,
                s.filing_date,
                s.cik,
                s.base_url,
                s.item_number,
                s.ts,
                'removal' AS event_type,
                r.name,
                r.role,
                r.effective_date
            FROM item502_summary s
            INNER JOIN item502_removal r ON s.cik = r.cik AND s.filing_date = r.filing_date
        """)
    finally:
        con.close()
