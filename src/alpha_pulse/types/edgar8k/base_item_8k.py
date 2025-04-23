import operator
from pydantic import BaseModel, Field
from typing import Optional, Annotated, Dict, List
    

from pydantic import BaseModel
from typing import Literal, Optional


class BaseItem8K(BaseModel):
    """Represents a parsed 8-K item."""
    parsed_text: str = Field(..., description="The parsed text content of the 8-K item")

    # Optional fields with default values
    cik: Optional[str] = Field(None, description="The CIK of the company")
    item_number: Optional[str] = Field(None, description="The number of the 8-K item")
    ex99_urls: Optional[str] = Field(None, description="The URLs of the EX-99 filings")
    url_8k: Optional[str] = Field(None, description="The URL of the 8-K filing")
    filing_date: Optional[str] = Field(None, description="The date of the 8-K filing")