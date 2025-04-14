"""State type definitions for Alpha Pulse."""

from typing import List, Optional
from pydantic import BaseModel, Field

from alpha_pulse.types.edgar import Edgar8kFilingData


class Edgar8kState(BaseModel):
    """State for the 8-K parser agent.
    
    Attributes:
        ticker: Ticker to process
        filingEntries: List of Edgar8kFilingData objects
    """
    ticker: str = Field(..., description="The ticker of the company to process")
    filingEntries: Optional[List[Edgar8kFilingData]] = Field(None, description="List of the 8-K filing data to process") 