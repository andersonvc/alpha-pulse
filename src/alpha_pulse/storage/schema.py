"""Database schema definitions for Alpha Pulse.

This module defines database schemas using Pydantic models as the source of truth.
Each table schema is generated from its corresponding Pydantic model, ensuring
type safety and consistency between the database and application code.
"""

from dataclasses import dataclass
from typing import List, Type
from pydantic import BaseModel

from alpha_pulse.types.dbtables.filing_entry import FilingRSSFeedEntry
from alpha_pulse.types.dbtables.parsed_8k_text import Parsed8KText
from alpha_pulse.types.dbtables.parsed_ex99_text import ParsedEX99Text
from alpha_pulse.types.dbtables.analyzed_ex99_text import AnalyzedEX99Text
from alpha_pulse.storage.db_utils import generate_create_statement

@dataclass
class TableSchema:
    """Schema definition for a database table.
    
    Attributes:
        name: Name of the table
        model: Pydantic model class for the table
        create_statement: SQL statement to create the table
        indexes: List of SQL statements to create indexes
    """
    name: str
    model: Type[BaseModel]
    create_statement: str
    primary_key: List[str]
    indexes: List[str] = None

# Table schemas
FILED_8K_LISTING = TableSchema(
    name="filed_8k_listing",
    model=FilingRSSFeedEntry,
    create_statement=generate_create_statement(FilingRSSFeedEntry, "filed_8k_listing", ['base_url']),
    primary_key=['base_url'],
    indexes=[
        "CREATE INDEX IF NOT EXISTS idx_filed_8k_listing_cik ON filed_8k_listing(cik)",
        "CREATE INDEX IF NOT EXISTS idx_filed_8k_listing_updated_date ON filed_8k_listing(updated_date)"
    ]
)

PARSED_8K_TEXT = TableSchema(
    name="parsed_8k_text",
    model=Parsed8KText,
    create_statement=generate_create_statement(Parsed8KText, "parsed_8k_text", ['cik', 'filing_date', 'item_number']),
    primary_key=['cik','filing_date', 'item_number'],
)

PARSED_EX99_TEXT = TableSchema(
    name="parsed_ex99_text",
    model=ParsedEX99Text,
    create_statement=generate_create_statement(ParsedEX99Text, "parsed_ex99_text", ['cik', 'filing_date', 'ex99_id']),
    primary_key=['cik','filing_date', 'ex99_id'],
)

ANALYZED_EX99_TEXT = TableSchema(
    name="analyzed_ex99_text",
    model=AnalyzedEX99Text,
    create_statement=generate_create_statement(AnalyzedEX99Text, "analyzed_ex99_text", ['cik', 'filing_date', 'ex99_id']),
    primary_key=['cik','filing_date', 'ex99_id'],
)
# List of all tables
TABLES = {
    'filed_8k_listing':FILED_8K_LISTING,
    'parsed_8k_text':PARSED_8K_TEXT,
    'parsed_ex99_text':PARSED_EX99_TEXT,
    'analyzed_ex99_text':ANALYZED_EX99_TEXT
}