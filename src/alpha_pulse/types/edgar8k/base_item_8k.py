"""Base class for 8-K item types."""

from pydantic import BaseModel, Field
from typing import Optional

class BaseItem8K(BaseModel):
    """Base class for parsed 8-K items.
    
    Attributes:
        parsed_text: The parsed text content of the 8-K item
        cik: The CIK of the company
        item_number: The number of the 8-K item
        ex99_urls: The URLs of the EX-99 filings
        url_8k: The URL of the 8-K filing
        filing_date: The date of the 8-K filing
    """
    parsed_text: str = Field(
        ...,
        description="The parsed text content of the 8-K item"
    )
    cik: Optional[str] = Field(
        None,
        description="The CIK of the company"
    )
    item_number: Optional[str] = Field(
        None,
        description="The number of the 8-K item"
    )
    ex99_urls: Optional[str] = Field(
        None,
        description="The URLs of the EX-99 filings"
    )
    url_8k: Optional[str] = Field(
        None,
        description="The URL of the 8-K filing"
    )
    filing_date: Optional[str] = Field(
        None,
        description="The date of the 8-K filing"
    )