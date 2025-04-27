"""Database operations using DuckDB."""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple
from dataclasses import dataclass
import logging
import json

from alpha_pulse.types.edgar8k import Item8K_801, Item8K_502

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
    
    ITEMS_8K_502 = TableInfo(
        name="items_8k_502",
        model=Item8K_502,
        primary_key=["cik", "filing_date", "item_number"]
    )
    
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """Initialize DuckDB connection.
        
        Args:
            db_path: Path to the DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self.create_8k_tables()

    def _connect(self) -> None:
        """Establish database connection."""
        if self.conn is not None:
            self.conn.close()
        self.conn = duckdb.connect(str(self.db_path) if self.db_path else ':memory:')

    def _get_model_fields(self, model: type) -> List[str]:
        """Get field names from a Pydantic model.
        
        Args:
            model: Pydantic model class
            
        Returns:
            List of field names
        """
        return list(model.model_fields.keys())

    def create_8k_tables(self) -> None:
        """Create tables for storing State8K records with Item8K items."""
        # Create tables for each item type
        for table_info in [self.ITEMS_8K_801, self.ITEMS_8K_502]:
            # Get all fields from the model
            fields = self._get_model_fields(table_info.model)
            
            # Create column definitions
            columns = []
            for field in fields:
                columns.append(f"{field} TEXT")
            
            # Create table with composite primary key
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_info.name} (
                    {', '.join(columns)},
                    PRIMARY KEY ({', '.join(table_info.primary_key)})
                )
            """)
            
        # Create raw 8-K data table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_8k_data (
                cik TEXT,
                filing_date TEXT,
                raw_text TEXT,
                items TEXT,
                url_8k TEXT,
                url_ex99 TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (cik, filing_date, items)
            )
        """)

    def insert_8k_items(self, items: Union[Dict[str, Any], pd.DataFrame], item_type: str = "801") -> None:
        """Insert 8-K items into the database.
        
        Args:
            items: Either a dictionary of item_number to Item8K or a DataFrame
            item_type: Type of 8-K item ("801" or "502")
        """
        item_type = item_type.replace('.', '')
        if not isinstance(items, pd.DataFrame):
            raise ValueError("items must be a DataFrame")
            
        # Select the appropriate table info
        table_info = self.ITEMS_8K_801 if item_type == "801" else self.ITEMS_8K_502
            
        # Get model fields and their types
        fields = self._get_model_fields(table_info.model)
        field_types = {}
        for field_name, field in table_info.model.model_fields.items():
            field_types[field_name] = field.annotation
            
        # Debug logging before processing
        logging.info("Original DataFrame:")
        logging.info(items.info())
        logging.info("Original DataFrame head:")
        logging.info(items.head())
            
        # Ensure DataFrame has all required columns in the correct order
        for field in fields:
            if field not in items.columns:
                if field == 'individuals':
                    items[field] = '[]'
                elif field_types[field] == int:
                    items[field] = 0
                elif field_types[field] == bool:
                    items[field] = False
                else:
                    items[field] = ''
            else:
                # Ensure required fields are not empty
                if field in ['cik', 'filing_date', 'item_number']:
                    items[field] = items[field].fillna('')
                    if items[field].empty or items[field].isna().all():
                        raise ValueError(f"Required field {field} is empty or contains only NULL values")
                # Handle numeric fields
                elif field_types[field] == int:
                    items[field] = items[field].fillna(0)
                elif field_types[field] == bool:
                    items[field] = items[field].fillna(False)
                    
        # Reorder columns to match table structure
        items = items[fields]
            
        # Handle individuals field if present
        if 'individuals' in items.columns:
            def handle_individuals(x):
                try:
                    if isinstance(x, (list, dict)):
                        return json.dumps(x)
                    if isinstance(x, str):
                        return x
                    if pd.isna(x).any() if isinstance(x, pd.Series) else pd.isna(x):
                        return '[]'
                    return '[]'
                except Exception as e:
                    logging.error(f"Error handling individuals field: {str(e)}")
                    return '[]'
                    
            items['individuals'] = items['individuals'].apply(handle_individuals)
            
        # Debug logging after processing
        logging.info("Processed DataFrame:")
        logging.info(items.info())
        logging.info("Processed DataFrame head:")
        logging.info(items.head())
        logging.info("Required fields check:")
        for field in ['cik', 'filing_date', 'item_number']:
            logging.info(f"{field} values: {items[field].tolist()}")
            
        # Register the DataFrame as a temporary table
        self.conn.register('temp_df', items)
        
        # Create column definitions with proper type casting
        columns = []
        for field in fields:
            if field_types[field] == int:
                columns.append(f"CAST({field} AS INTEGER) as {field}")
            elif field_types[field] == bool:
                columns.append(f"CAST({field} AS BOOLEAN) as {field}")
            else:
                columns.append(field)
        
        # Debug logging
        logging.info(f"Table name: {table_info.name}")
        logging.info(f"Fields: {fields}")
        logging.info(f"Columns: {columns}")
        
        # Insert into the main table
        query = f"""
            INSERT INTO {table_info.name} ({', '.join(fields)})
            SELECT {', '.join(columns)}
            FROM temp_df
        """
        logging.info(f"SQL Query: {query}")
        
        self.conn.execute(query)
        
        # Unregister the temporary table
        self.conn.unregister('temp_df')

    def insert_raw_8k_data(self, state: 'State8K') -> None:
        """Insert raw 8-K data into the database.
        
        Args:
            state: State8K object containing raw filing data
        """
        # Convert state to dictionary
        data = {
            'cik': state.cik,
            'filing_date': state.filing_date,
            'raw_text': state.raw_text,
            'items': state.items,
            'url_8k': state.url_8k or '',
            'url_ex99': state.url_ex99 or ''
        }
        
        # Create DataFrame
        df = pd.DataFrame([data])
        
        # Register as temporary table
        self.conn.register('temp_df', df)
        
        # Insert into raw_8k_data table
        self.conn.execute("""
            INSERT INTO raw_8k_data (cik, filing_date, raw_text, items, url_8k, url_ex99)
            SELECT cik, filing_date, raw_text, items, url_8k, url_ex99
            FROM temp_df
        """)
        
        # Unregister temporary table
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

    def get_all_tables(self) -> List[str]:
        """Get a list of all tables in the database.
        
        Returns:
            List of table names
        """
        with self._get_connection() as conn:
            tables = conn.execute("SHOW TABLES").fetchall()
            return [table[0] for table in tables]

    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """Get all data from a specific table.
        
        Args:
            table_name: Name of the table to query
            
        Returns:
            DataFrame containing all data from the table
        """
        with self._get_connection() as conn:
            return conn.execute(f"SELECT * FROM {table_name}").fetchdf()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a new database connection.
        
        Returns:
            DuckDB connection
        """
        return duckdb.connect(str(self.db_path) if self.db_path else ':memory:')

    def get_all_filings(self) -> Dict[str, pd.DataFrame]:
        """Get all filings from the database.
        
        Returns:
            DataFrame containing all filings with their parsed items
        """
        with self._get_connection() as conn:
            recs_801 = conn.execute(f"""
                SELECT DISTINCT cik, filing_date, item_number, event_type, event_summary, sentiment
                FROM {self.ITEMS_8K_801.name}
                ORDER BY filing_date DESC, cik
            """).df()
            recs_502 = conn.execute(f"""
                SELECT DISTINCT *
                FROM {self.ITEMS_8K_502.name}
                ORDER BY filing_date DESC, cik
            """).df()
            return {'801': recs_801, '502': recs_502}

    async def __aenter__(self) -> 'DuckDBManager':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()

    def __enter__(self) -> 'DuckDBManager':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None

# Initialize default database manager
db_manager = DuckDBManager(db_path="data/alpha_pulse.db") 