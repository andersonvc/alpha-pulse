from pydantic import BaseModel, Field
from typing import Optional, Annotated, Dict, List
    

from pydantic import BaseModel
from typing import Optional

from alpha_pulse.types.edgar8k import BaseItem8K
    

class State8K(BaseModel):
    """State 8-K processing.
    
    Attributes:
        raw_text: The raw text of the 8-K filing
        items: List of item identifiers to process
        parsed_items: Dictionary mapping item identifiers to their parsed content
    """
    cik: str = Field(..., description="The CIK of the company")
    filing_date: str = Field(..., description="The date of the 8-K filing")
    raw_text: str = Field(..., description="The raw text of the 8-K filing")
    items: str = Field(..., description="List of item identifiers to process")
    parsed_items: Optional[Dict[str, BaseItem8K]] = Field(
        None,
        description="Dictionary mapping item identifiers to their parsed content"
    )
    url_8k: Optional[str] = Field(None, description="The URL of the 8-K filing")
    url_ex99: Optional[str] = Field(None, description="The URLs of the EX-99 filings")
