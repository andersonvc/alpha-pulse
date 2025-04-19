"""Simple types for 8-K filing processing."""

import operator
from pydantic import BaseModel, Field
from typing import Optional, Annotated, Dict, List

from alpha_pulse.types.edgar8k import Parsed8KItem
    

from pydantic import BaseModel
from typing import Literal, Optional

SentimentType = Literal["positive", "negative", "neutral"]

EventType = Literal[
    "M&A",
    "Dividend",
    "Stock Split",
    "Share Repurchase",
    "Earnings Update",
    "Financial Guidance",
    "Restatement",
    "Legal Action",
    "Regulatory Update",
    "Settlement",
    "Compliance Notice",
    "Product Launch",
    "Product Recall",
    "Cybersecurity Incident",
    "Operational Disruption",
    "Plant Closure",
    "Leadership Commentary",
    "Governance Update",
    "Joint Venture",
    "Market Entry/Exit",
    "Strategic Restructuring",
    "Investor Communication",
    "Environmental Impact",
    "Public Response",
    "Other"
]

class Simple8KItem(BaseModel):
    """Represents a parsed 8-K item."""
    parsed_text: str = Field(..., description="The parsed text content of the 8-K item")

    # Optional fields with default values
    cik: Optional[str] = Field(None, description="The CIK of the company")
    item_number: Optional[str] = Field(None, description="The number of the 8-K item")
    ex99_urls: Optional[str] = Field(None, description="The URLs of the EX-99 filings")
    url_8k: Optional[str] = Field(None, description="The URL of the 8-K filing")
    filing_date: Optional[str] = Field(None, description="The date of the 8-K filing")


class Simple8KItem_801(Simple8KItem):
    """Represents an analysis of an 8-K Item 8.01 filing."""

    event_type: EventType = Field(..., description="The type of event described in the 8-K item")
    sentiment: int = Field(..., description="The sentiment of the 8-K item (-1=negative, 0=neutral, 1=positive)")
    event_summary: str = Field(..., description="A summary of the event described in the 8-K item")
    key_takeaway: str = Field(..., description="A key takeaway from the 8-K item")
    probable_price_move: bool = Field(..., description="Whether the price of the company is likely to move as a result of the event")
    price_move_reason: str = Field(..., description="The reason for the probable price move")   
    is_financially_material: bool = Field(..., description="Whether the event is financially material")
    is_operational_impact: bool = Field(..., description="Whether the event is an operational impact")
    is_related_to_prior: bool = Field(..., description="Whether the event is related to a prior event")
    is_recent_event: bool = Field(..., description="Whether the event is recent")
    unexpected_timing: bool = Field(..., description="Whether the event is unexpected timing")  
    mentioned_companies: str = Field(..., description="The companies mentioned in the 8-K item")
    mentioned_tickers: str = Field(..., description="The tickers mentioned in the 8-K item")
    keywords: str = Field(..., description="The keywords in the 8-K item")
    strategic_signal: bool = Field(..., description="Whether the event is a strategic signal")
    priority_shift_detected: bool = Field(..., description="Whether the event is a priority shift")

    

class SimpleState8K(BaseModel):
    """State for simple 8-K processing.
    
    Attributes:
        raw_text: The raw text of the 8-K filing
        items: List of item identifiers to process
        parsed_items: Dictionary mapping item identifiers to their parsed content
    """
    cik: str = Field(..., description="The CIK of the company")
    filing_date: str = Field(..., description="The date of the 8-K filing")
    raw_text: str = Field(..., description="The raw text of the 8-K filing")
    items: str = Field(..., description="List of item identifiers to process")
    parsed_items: Optional[Dict[str, Simple8KItem]] = Field(
        None,
        description="Dictionary mapping item identifiers to their parsed content"
    )
    url_8k: Optional[str] = Field(None, description="The URL of the 8-K filing")
    url_ex99: Optional[str] = Field(None, description="The URLs of the EX-99 filings")
    #parsed_items: Optional[Annotated[dict[str, Simple8KItem],operator.or_]]


class ExtractedUrls(BaseModel):
    url_8k: str
    url_ex99: str