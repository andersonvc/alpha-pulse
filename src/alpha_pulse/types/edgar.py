"""Filing type definitions for Alpha Pulse."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Edgar8kFilingData(BaseModel):
    """Represents a single SEC EDGAR 8-K filing URL with its metadata.
    
    Attributes:
        filing_date: The date the filing was submitted to the SEC
        root_url: The root URL of the filing index page
        item_type: List of item numbers covered in the filing
        filing_url: The URL to access the filing document
        raw_text: The raw text of the filing
    """
    cik: Optional[str] = Field(None, description="The company CIK code")
    filing_date: str = Field(..., description="The date the filing was submitted to the SEC")
    root_url: str = Field(..., description="The root URL of the filing index page")
    item_type: List[str] = Field(..., description="List of item numbers covered in the filing")
    filing_url: Optional[str] = Field(None, description="The URL to access the filing document")
    ex99_urls: Optional[List[str]] = Field(None, description="The URLs to access the EX-99.n filing documents")
    raw_text: Optional[str] = Field(None, description="The raw text of the filing")
    raw_ex99_texts: Optional[List[str]] = Field(None, description="The raw text of the EX-99.n filing documents")
    parsed_8k: Optional[dict] = Field(None, description="The parsed 8-K filing")
    parsed_ex99: Optional[list[str]] = Field(None, description="The parsed EX-99.n filing")


class Edgar8kItemAnalysis(BaseModel):
    """Represents an analysis of a single item in a SEC EDGAR 8-K filing.
    
    Attributes:
        item_number: The item number of the filing
        event_sentiment: The sentiment of the event in the filing
        event_sentiment_rationale: The rationale for the event sentiment
        event_expected: Whether the event is expected, unexpected, or unknown
        event_expected_rationale: The rationale for the event being expected or unexpected
        event_material: Whether the event is material, non-material, or unknown
        event_material_rationale: The rationale for the event being material or non-material
    """ 
    item_number: str = Field(..., description="The item number of the filing")
    event_sentiment: Optional[str] = Field(None, description="The sentiment of the event in the filing")
    event_sentiment_rationale: Optional[str] = Field(None, description="The rationale for the event sentiment")
    event_expected: Optional[str] = Field(None, description="Whether the event is expected, unexpected, or unknown")
    event_expected_rationale: Optional[str] = Field(None, description="The rationale for the event being expected or unexpected")
    event_material: Optional[str] = Field(None, description="Whether the event is material, non-material, or unknown")
    event_material_rationale: Optional[str] = Field(None, description="The rationale for the event being material or non-material")

class Edgar8kFilingAnalysis(BaseModel):
    """Represents an analysis of a single SEC EDGAR 8-K filing.
    
    Attributes:
        items: List of Edgar8kItemAnalysis objects
        summary: A summary of the events in the 8-K filing
        related_companies: A list of companies involved in the events described in the 8-K filing
    """
    items: List[Edgar8kItemAnalysis] = Field(..., description="List of Edgar8kItemAnalysis objects")
    summary: str = Field(..., description="A summary of the events in the 8-K filing")
    related_companies: Optional[List[str]] = Field([], description="A list of companies involved in the events described in the 8-K filing")
