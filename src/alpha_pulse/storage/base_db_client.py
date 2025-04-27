import duckdb
import time
from pathlib import Path
from typing import Any, List, Type, Dict
from pydantic import BaseModel
from alpha_pulse.storage.db_utils import generate_create_statement
from alpha_pulse.storage.schema import TABLES

DB_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'alpha_pulse.duckdb'


class DuckDBClient:
    def __init__(self, read_only: bool = False, retries: int = 3, retry_delay: float = 1.0):
        self.db_path = DB_PATH
        self.read_only = read_only
        self.retries = retries
        self.retry_delay = retry_delay
        self.conn = None

    def _ensure_directory(self):
        if isinstance(self.db_path, Path) and self.db_path != ':memory:':
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        if self.conn is not None:
            return
        self._ensure_directory()

        attempt = 0
        while attempt <= self.retries:
            try:
                self.conn = duckdb.connect(
                    database=str(self.db_path),
                    read_only=self.read_only
                )
                print(f"Connected to DuckDB at {self.db_path} (read_only={self.read_only})")
                return
            except duckdb.IOException as e:
                if "Conflicting lock" in str(e) and attempt < self.retries:
                    print(f"Database locked. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    attempt += 1
                else:
                    raise

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Connection closed.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _startup_db(self):
        self.connect()
        for table in TABLES.values():
            if not self.table_exists(table.name):
                create_table_sql = generate_create_statement(table.model, table.name, table.primary_key)
                self.execute(create_table_sql)

    def execute(self, query: str, params: tuple = ()) -> duckdb.DuckDBPyConnection:
        self.connect()
        return self.conn.execute(query, params)

    def executemany(self, query: str, params_list: List[tuple]):
        self.connect()
        return self.conn.executemany(query, params_list)

    def table_exists(self, table_name: str) -> bool:
        query = """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """
        result = self.execute(query, (table_name.lower(),)).fetchone()
        return result[0] > 0

    def fetchall_dict(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        self.connect()
        cursor = self.conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetchdf(self, query: str, params: tuple = ()):
        self.connect()
        return self.conn.execute(query, params).fetchdf()

    def filter_out_existing_primary_keys(self, table_name: str, keys: List[tuple]) -> List[tuple]:
        if not keys:
            return []

        table_config = TABLES.get(table_name)
        if not table_config:
            raise ValueError(f"Table {table_name} not found in schema.")

        primary_keys = table_config.primary_key

        if len(primary_keys) == 1:
            pk_field = primary_keys[0]
            placeholders = ', '.join('?' for _ in keys)
            query = f"SELECT {pk_field} FROM {table_name} WHERE {pk_field} IN ({placeholders})"
            params = [k if isinstance(k, str) else k[0] for k in keys]
        else:
            where_clauses = [' AND '.join(f"{pk}=?" for pk in primary_keys) for _ in keys]
            query = f"""
            SELECT {', '.join(primary_keys)}
            FROM {table_name}
            WHERE {' OR '.join(f'({clause})' for clause in where_clauses)}
            """
            params = [item for key in keys for item in (key if isinstance(key, tuple) else (key,))]

        self.connect()
        cursor = self.conn.execute(query, params)
        existing_keys = cursor.fetchall()

        if len(primary_keys) == 1:
            existing_keys = [k[0] for k in existing_keys]

        return list(set(keys) - set(existing_keys))

    def insert_records(self, table_name: str, records: List[BaseModel]):

        if not records:
            return
        
        if isinstance(records, BaseModel):
            records = [records]

        if not isinstance(records[0], BaseModel):
            raise ValueError("Records must be a list of Pydantic models")

        table_fields = list(records[0].__fields__.keys())
        column_list = ', '.join(table_fields)
        placeholders = ', '.join(['?' for _ in table_fields])
        insert_statement = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

        records = [r for r in records if r is not None]
        values = [
            tuple(getattr(record, field) for field in table_fields)
            for record in records
        ]

        self.executemany(insert_statement, values)
        print(f"Inserted {len(values)} records into {table_name}")
