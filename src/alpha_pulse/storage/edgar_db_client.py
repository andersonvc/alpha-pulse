from typing import List, Any

from alpha_pulse.storage.base_db_client import DuckDBClient
from alpha_pulse.storage.schema import TABLES
from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
class EdgarDBClient(DuckDBClient):
    def __init__(self, read_only: bool = False, retries: int = 3, retry_delay: float = 1.0):
        super().__init__(read_only, retries, retry_delay)

    def create_tables(self):
        """Create the tables in the database."""
        for table in TABLES:
            self.create_table(table)
    
    def insert_filings(self, entries: List[Any]):
        """Insert the filings into the database."""

        if not isinstance(entries, list):
            entries = [entries]

        match entries[0]:
            case FilingRSSFeedEntry():
                table = 'filed_8k_listing'
            case _:
                raise ValueError("entries not a valid type")
            
        for entry in entries:
            self.insert(table, entry)
    
    def get_unprocessed_filings(self) -> List[FilingRSSFeedEntry]:
        """Get all unprocessed filings."""
        query = """
            SELECT * FROM filed_8k_listing WHERE processed = FALSE
        """

        try: 
            self.connect()
            res = self.fetchall_dict(query)

            # convert list to pydantic
            table_config = TABLES['filed_8k_listing']
            results = [table_config.model(**result) for result in res]
            return results
        except Exception as e:
            print(e)
            return []
        finally:
            self.close()
    
    def update_processed_filings(self, base_urls: List[str]):
        """Update the processed filings."""
        if not base_urls:
            return

        try:
            self.connect()
            
            # Create placeholders (?, ?, ?, ...)
            placeholders = ', '.join(['?'] * len(base_urls))
            
            query = f"""
                UPDATE filed_8k_listing
                SET processed = TRUE
                WHERE base_url IN ({placeholders})
            """
            
            self.execute(query, tuple(base_urls))
            
        except Exception as e:
            print(e)
        finally:
            self.close()
    
    async def update_url_8k(self, base_url: str, url_8k: str, url_ex99: str, raw_8k_text: str):
        """Update the URL of the 8-K filing."""
        
        query = """
            UPDATE filed_8k_listing
            SET url_8k = ?, url_ex99 = ?, raw_8k_text = ?
            WHERE base_url = ?
        """
        self.execute(query, (url_8k, url_ex99, raw_8k_text, base_url))
