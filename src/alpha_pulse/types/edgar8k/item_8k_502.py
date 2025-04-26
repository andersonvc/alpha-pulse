"""Item 5.02 type for 8-K filings."""

from typing import List, Literal
from pydantic import BaseModel, Field

from alpha_pulse.types.edgar8k.base_item_8k import BaseItem8K

class IndividualChange(BaseModel):
    """Represents a change in executive or director position.
    
    Attributes:
        name: Name of the individual
        role: Position or role of the individual
        event_type: Type of change event
        effective_date: When the change takes effect
        reason_for_change: Explanation for the change
        background: Brief background of the individual
        compensation_details: Summary of compensation information
        board_committee_assignments: Committee assignments if applicable
    """
    name: str = Field(
        ...,
        description="Name of the individual"
    )
    role: str = Field(
        ...,
        description="Position or role of the individual"
    )
    event_type: Literal["resignation", "appointment", "termination", "retirement", "election"] = Field(
        ...,
        description="Type of change event"
    )
    effective_date: str = Field(
        ...,
        description="When the change takes effect"
    )
    reason_for_change: str = Field(
        ...,
        description="Explanation for the change"
    )
    background: str = Field(
        ...,
        description="Brief background of the individual"
    )
    compensation_details: str = Field(
        ...,
        description="Summary of compensation information"
    )
    board_committee_assignments: str = Field(
        ...,
        description="Committee assignments if applicable"
    )

class Item8K_502(BaseItem8K):
    """Represents an analysis of an 8-K Item 5.02 filing.
    
    This class captures information about executive and director changes
    reported in Item 5.02 of an 8-K filing.
    
    Attributes:
        individuals: List of individual changes reported in the filing
    """
    individuals: List[IndividualChange] = Field(
        ...,
        description="List of individual changes reported in the filing"
    )