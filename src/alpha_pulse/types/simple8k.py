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

class Simple8KItem_801(Simple8KItem):
    """Represents an analysis of an 8-K Item 8.01 filing.
    
    This model captures various aspects of an 8-K Item 8.01 filing including:
    - Event classification
    - Materiality assessment
    - Impact analysis
    - Timing and context
    - Strategic implications
    """
    
    # Event Classification
    event_type: EventType = Field(..., description="Classification of the event type")
    sentiment: SentimentType = Field(..., description="Sentiment of the event")
    event_summary: str = Field(..., description="A short summary of the event")
    most_relevant_takeaway: str = Field(..., description="A short summary of the most relevant takeaway from the event")
    stock_price_impact: bool = Field(..., description="Will event impact the company's stock price")
    stock_price_impact_reasoning: str = Field(..., description="The reasoning behind the expected impact on the company's stock price")

    # Materiality Assessment
    is_material: bool = Field(..., description="Whether the event is material")
    is_related_to_prior: bool = Field(..., description="Whether the event relates to prior disclosures")
    
    # Impact Analysis
    is_financial_impact: bool = Field(..., description="Whether the event has financial implications")
    is_operational_impact: bool = Field(..., description="Whether the event affects operations")
    is_market_reaction_expected: bool = Field(..., description="Whether market reaction is expected")
    
    # Timing and Context
    is_recent_event: bool = Field(..., description="Whether the event occurred recently")
    unexpected_timing: bool = Field(..., description="Whether the timing was unexpected")
    
    # Strategic Context
    list_of_mentioned_companies: List[str] = Field(..., description="A list of companies mentioned in the event")
    list_of_keywords: List[str] = Field(..., description="A list of keywords that are relevant to the event")
    strategic_signal: bool = Field(..., description="Whether the event signals strategic change")
    priority_shift: bool = Field(..., description="Whether priorities have shifted")
    

class SimpleState8K(BaseModel):
    """State for simple 8-K processing.
    
    Attributes:
        raw_text: The raw text of the 8-K filing
        items: List of item identifiers to process
        parsed_items: Dictionary mapping item identifiers to their parsed content
    """
    raw_text: str = Field(..., description="The raw text of the 8-K filing")
    items: str = Field(..., description="List of item identifiers to process")
    parsed_items: Optional[Dict[str, Simple8KItem]] = Field(
        None,
        description="Dictionary mapping item identifiers to their parsed content"
    )
    #parsed_items: Optional[Annotated[dict[str, Simple8KItem],operator.or_]]