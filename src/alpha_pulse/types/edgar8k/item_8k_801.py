"""Item 8.01 type for 8-K filings."""

from typing import Literal
from pydantic import Field
from alpha_pulse.types.edgar8k.base_item_8k import BaseItem8K

# Event types for Item 8.01
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

class Item8K_801(BaseItem8K):
    """Represents an analysis of an 8-K Item 8.01 filing.
    
    Attributes:
        event_type: The type of event described in the 8-K item
        sentiment: The sentiment of the 8-K item (-1=negative, 0=neutral, 1=positive)
        event_summary: A summary of the event described in the 8-K item
        key_takeaway: A key takeaway from the 8-K item
        probable_price_move: Whether the price of the company is likely to move
        price_move_reason: The reason for the probable price move
        is_financially_material: Whether the event is financially material
        is_operational_impact: Whether the event is an operational impact
        is_related_to_prior: Whether the event is related to a prior event
        is_recent_event: Whether the event is recent
        unexpected_timing: Whether the event is unexpected timing
        mentioned_companies: The companies mentioned in the 8-K item
        mentioned_tickers: The tickers mentioned in the 8-K item
        keywords: The keywords in the 8-K item
        strategic_signal: Whether the event is a strategic signal
        priority_shift_detected: Whether the event is a priority shift
    """
    event_type: EventType = Field(
        ...,
        description="The type of event described in the 8-K item"
    )
    sentiment: int = Field(
        ...,
        description="The sentiment of the 8-K item (-1=negative, 0=neutral, 1=positive)"
    )
    event_summary: str = Field(
        ...,
        description="A summary of the event described in the 8-K item"
    )
    key_takeaway: str = Field(
        ...,
        description="A key takeaway from the 8-K item"
    )
    probable_price_move: bool = Field(
        ...,
        description="Whether the price of the company is likely to move"
    )
    price_move_reason: str = Field(
        ...,
        description="The reason for the probable price move"
    )
    is_financially_material: bool = Field(
        ...,
        description="Whether the event is financially material"
    )
    is_operational_impact: bool = Field(
        ...,
        description="Whether the event is an operational impact"
    )
    is_related_to_prior: bool = Field(
        ...,
        description="Whether the event is related to a prior event"
    )
    is_recent_event: bool = Field(
        ...,
        description="Whether the event is recent"
    )
    unexpected_timing: bool = Field(
        ...,
        description="Whether the event is unexpected timing"
    )
    mentioned_companies: str = Field(
        ...,
        description="The companies mentioned in the 8-K item"
    )
    mentioned_tickers: str = Field(
        ...,
        description="The tickers mentioned in the 8-K item"
    )
    keywords: str = Field(
        ...,
        description="The keywords in the 8-K item"
    )
    strategic_signal: bool = Field(
        ...,
        description="Whether the event is a strategic signal"
    )
    priority_shift_detected: bool = Field(
        ...,
        description="Whether the event is a priority shift"
    )