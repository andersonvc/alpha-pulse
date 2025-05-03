"""Base class for 8-K item types."""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, date

class FilingRSSFeedEntry(BaseModel):
    """
    Atom RSS feed entry containing list of latest 8-K filings.
    Storing this value in our data base to avoid re-downloading / processing the same filing.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    cik: str = Field(..., description="The company's CIK identifier")
    base_url: str = Field(..., description="The base URL of the filing")
    item_list: str = Field(..., description="The list of items in the 8-K filing")
    ts: datetime = Field(..., description="Timestamp of exactly when the filing was uploaded")
    filing_date: date = Field(..., description="Date of the 8-K filing")
    processed: Optional[bool] = Field(False, description="Whether the filing has been processed")
    url_8k: Optional[str] = Field('', description="The URL of the 8-K filing")
    url_ex99: Optional[str] = Field('', description="The URL of the EX-99 filings")
    raw_8k_text: Optional[str] = Field('', description="The raw text of the 8-K filing")
    ticker: Optional[str] = Field('', description="The ticker of the company")
    market_cap: Optional[float] = Field(0, description="The market cap of the company")
    sic: Optional[str] = Field('', description="The SIC code of the company")

    @field_validator('ts')
    def must_be_timezone_aware(cls, v):
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("event_time must be timezone-aware")
        return v
