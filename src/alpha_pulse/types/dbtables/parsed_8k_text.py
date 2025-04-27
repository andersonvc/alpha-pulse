"""Base class for 8-K item types."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, date

class Parsed8KText(BaseModel):
    """
    Extracted / formatted text from html of 8-K filing. Items are stored separately in this table.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    cik: str = Field(..., description="The company's CIK identifier")
    item_number: str = Field(..., description="The item number of the 8-K filing")
    base_url: str = Field(..., description="The base URL of the filing")
    item_text: str = Field(..., description="The extracted / formatted text of the item")
    ts: datetime = Field(..., description="Timestamp of exactly when the item was extracted")
    filing_date: date = Field(..., description="Date of the 8-K filing")

    @field_validator('ts')
    def must_be_timezone_aware(cls, v):
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("event_time must be timezone-aware")
        return v
