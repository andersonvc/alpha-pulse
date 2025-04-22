"""Database operations using DuckDB."""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import json

from alpha_pulse.types.simple8k import Simple8KItem_801

def read_from_duckdb(
    db_path: Union[str, Path],
    table_name: str,
    columns: Optional[List[str]] = None,
    where_clause: Optional[str] = None,
    params: Optional[List[Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None
) -> pd.DataFrame:
    """Read data from a DuckDB table.
    
    Args:
        db_path: Path to the DuckDB database file
        table_name: Name of the table to read from
        columns: List of columns to select (None for all columns)
        where_clause: SQL WHERE clause (without the WHERE keyword)
        params: Parameters for the WHERE clause
        order_by: SQL ORDER BY clause (without the ORDER BY keyword)
        limit: Maximum number of rows to return
        
    Returns:
        DataFrame containing the query results
    """
    with duckdb.connect(str(db_path)) as conn:
        # Build the SELECT clause
        select_clause = "*" if columns is None else ", ".join(columns)
        
        # Build the query
        query = f"SELECT {select_clause} FROM {table_name}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
            
        if order_by:
            query += f" ORDER BY {order_by}"
            
        if limit is not None:
            query += f" LIMIT {limit}"
            
        # Execute the query
        if params:
            return conn.execute(query, params).df()
        else:
            return conn.execute(query).df()

class DuckDBManager:
    """Manager for DuckDB operations."""
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize DuckDB connection.
        
        Args:
            db_path: Path to the DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path) if db_path else ':memory:')
        # Create tables on initialization
        self.create_simple8k_tables()


    def query(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            DataFrame containing query results
        """
        return self.conn.execute(sql).df()
        
        
    def export_to_parquet(self, table_name: str, output_path: Union[str, Path]):
        """Export table to Parquet file.
        
        Args:
            table_name: Name of the table to export
            output_path: Path to save Parquet file
        """
        self.conn.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)")
        
    def create_simple8k_tables(self):
        """Create tables for storing SimpleState8K records with Simple8KItem_801 items."""
        
        # Create table for Simple8KItem_801 items
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS simple8k_items_801 (
                cik TEXT,
                item_number TEXT,
                ex99_urls TEXT,
                url_8k TEXT,
                filing_date TEXT,
                parsed_text TEXT,
                event_type TEXT,
                sentiment INTEGER,
                event_summary TEXT,
                key_takeaway TEXT,
                probable_price_move BOOLEAN,
                price_move_reason TEXT,
                is_financially_material BOOLEAN,
                is_operational_impact BOOLEAN,
                is_related_to_prior BOOLEAN,
                is_recent_event BOOLEAN,
                unexpected_timing BOOLEAN,
                mentioned_companies TEXT,
                mentioned_tickers TEXT,
                keywords TEXT,
                strategic_signal BOOLEAN,
                priority_shift_detected BOOLEAN,
                PRIMARY KEY (cik, filing_date, item_number)
            )
        """)
        
                    
    def insert_simple8k_items(self, items: Union[Dict[str, Simple8KItem_801], pd.DataFrame]):
        """Insert Simple8KItem_801 items into the database.
        
        Args:
            items: Either a dictionary of item_number to Simple8KItem_801 or a DataFrame
        """
        if isinstance(items, pd.DataFrame):
            # Register the DataFrame as a temporary table
            self.conn.register('temp_df', items)
            
            # Insert into the main table
            self.conn.execute("""
                INSERT INTO simple8k_items_801 (cik, item_number, ex99_urls, url_8k, filing_date, parsed_text, event_type, sentiment, event_summary, key_takeaway, probable_price_move, price_move_reason, is_financially_material, is_operational_impact, is_related_to_prior, is_recent_event, unexpected_timing, mentioned_companies, mentioned_tickers, keywords, strategic_signal, priority_shift_detected)
                SELECT cik, item_number, ex99_urls, url_8k, filing_date, parsed_text, event_type, sentiment, event_summary, key_takeaway, probable_price_move, price_move_reason, is_financially_material, is_operational_impact, is_related_to_prior, is_recent_event, unexpected_timing, mentioned_companies, mentioned_tickers, keywords, strategic_signal, priority_shift_detected
                FROM temp_df
            """)
            
            # Unregister the temporary table
            self.conn.unregister('temp_df')
        else:
            raise ValueError("items must be a DataFrame")
        
    
        
    def get_all_simple8k_items(self) -> pd.DataFrame:
        """Get all Simple8KItem_801 records from the database.
        
        Returns:
            DataFrame containing all Simple8KItem_801 records
        """
        return self.conn.execute("""
            SELECT * FROM simple8k_items_801
        """).df()
        
    def get_simple8k_items_by_cik(self, cik: str) -> pd.DataFrame:
        """Get Simple8KItem_801 records for a specific CIK.
        
        Args:
            cik: CIK of the company
            
        Returns:
            DataFrame containing Simple8KItem_801 records for the CIK
        """
        return self.conn.execute("""
            SELECT * FROM simple8k_items_801 
            WHERE cik = ?
        """, (cik,)).df()
        
    def get_simple8k_items_by_date(self, filing_date: str) -> pd.DataFrame:
        """Get Simple8KItem_801 records for a specific filing date.
        
        Args:
            filing_date: Filing date of the 8-K
            
        Returns:
            DataFrame containing Simple8KItem_801 records for the filing date
        """
        return self.conn.execute("""
            SELECT * FROM simple8k_items_801 
            WHERE filing_date = ?
        """, (filing_date,)).df()
        
    def get_simple8k_items_by_event_type(self, event_type: str) -> pd.DataFrame:
        """Get Simple8KItem_801 records for a specific event type.
        
        Args:
            event_type: Type of event to filter by
            
        Returns:
            DataFrame containing Simple8KItem_801 records for the event type
        """
        return self.conn.execute("""
            SELECT * FROM simple8k_items_801 
            WHERE event_type = ?
        """, (event_type,)).df()
        
        
    def close(self):
        """Close the database connection."""
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def check_table_exists_and_has_records(self, table_name: str) -> tuple[bool, int]:
        """Check if a table exists and has any records.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            Tuple of (exists: bool, record_count: int)
        """
        # Check if table exists
        exists = self.conn.execute(f"""
            SELECT COUNT(*) > 0 
            FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        """).fetchone()[0]
        
        if not exists:
            return False, 0
            
        # Count records if table exists
        count = self.conn.execute(f"""
            SELECT COUNT(*) 
            FROM {table_name}
        """).fetchone()[0]
        
        return True, count

db_manager = DuckDBManager(db_path="data/alpha_pulse.db") 