"""Database operations using DuckDB."""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass

from alpha_pulse.types.edgar8k import Item8K_801

@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    model: type
    primary_key: List[str]

class DuckDBManager:
    """Manager for DuckDB operations."""
    
    # Table definitions
    ITEMS_8K_801 = TableInfo(
        name="items_8k_801",
        model=Item8K_801,
        primary_key=["cik", "filing_date", "item_number"]
    )
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize DuckDB connection.
        
        Args:
            db_path: Path to the DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path) if db_path else ':memory:')
        self.create_8k_tables()

    def _get_model_fields(self, model: type) -> List[str]:
        """Get field names from a Pydantic model.
        
        Args:
            model: Pydantic model class
            
        Returns:
            List of field names
        """
        return list(model.model_fields.keys())

    def create_8k_tables(self) -> None:
        """Create tables for storing State8K records with Item8K_801 items."""
        # Get all fields from the model
        fields = self._get_model_fields(self.ITEMS_8K_801.model)
        
        # Create column definitions
        columns = []
        for field in fields:
            columns.append(f"{field} TEXT")
        
        # Create table with composite primary key
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.ITEMS_8K_801.name} (
                {', '.join(columns)},
                PRIMARY KEY ({', '.join(self.ITEMS_8K_801.primary_key)})
            )
        """)

    def insert_8k_items(self, items: Union[Dict[str, Item8K_801], pd.DataFrame]) -> None:
        """Insert Item8K_801 items into the database.
        
        Args:
            items: Either a dictionary of item_number to Item8K_801 or a DataFrame
        """
        if not isinstance(items, pd.DataFrame):
            raise ValueError("items must be a DataFrame")
            
        # Register the DataFrame as a temporary table
        self.conn.register('temp_df', items)
        
        # Insert into the main table
        columns = ", ".join(self._get_model_fields(self.ITEMS_8K_801.model))
        self.conn.execute(f"""
            INSERT INTO {self.ITEMS_8K_801.name} ({columns})
            SELECT {columns}
            FROM temp_df
        """)
        
        # Unregister the temporary table
        self.conn.unregister('temp_df')

    def get_all_8k_items(self) -> pd.DataFrame:
        """Get all Item8K_801 records from the database.
        
        Returns:
            DataFrame containing all Item8K_801 records
        """
        return self.conn.execute(f"SELECT * FROM {self.ITEMS_8K_801.name}").df()

    def get_8k_items_by_cik(self, cik: str) -> pd.DataFrame:
        """Get Item8K_801 records for a specific CIK.
        
        Args:
            cik: CIK of the company
            
        Returns:
            DataFrame containing Item8K_801 records for the CIK
        """
        return self.conn.execute(
            f"SELECT * FROM {self.ITEMS_8K_801.name} WHERE cik = ?",
            (cik,)
        ).df()

    def get_8k_items_by_date(self, filing_date: str) -> pd.DataFrame:
        """Get Item8K_801 records for a specific filing date.
        
        Args:
            filing_date: Filing date of the 8-K
            
        Returns:
            DataFrame containing Item8K_801 records for the filing date
        """
        return self.conn.execute(
            f"SELECT * FROM {self.ITEMS_8K_801.name} WHERE filing_date = ?",
            (filing_date,)
        ).df()

    def get_8k_items_by_event_type(self, event_type: str) -> pd.DataFrame:
        """Get Item8K_801 records for a specific event type.
        
        Args:
            event_type: Type of event to filter by
            
        Returns:
            DataFrame containing Item8K_801 records for the event type
        """
        return self.conn.execute(
            f"SELECT * FROM {self.ITEMS_8K_801.name} WHERE event_type = ?",
            (event_type,)
        ).df()

    def check_table_exists_and_has_records(self, table_name: str) -> Tuple[bool, int]:
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

    def get_all_filings(self) -> pd.DataFrame:
        """Get all filings from the database.
        
        Returns:
            DataFrame containing all filings with their parsed items
        """
        return self.conn.execute(f"""
            SELECT DISTINCT cik, filing_date, item_number, event_type, event_summary, sentiment
            FROM {self.ITEMS_8K_801.name}
            ORDER BY filing_date DESC, cik
        """).df()

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self) -> 'DuckDBManager':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

# Initialize default database manager
db_manager = DuckDBManager(db_path="data/alpha_pulse.db") 