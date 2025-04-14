"""Analysis type definitions for Alpha Pulse."""

from typing import List
from pydantic import BaseModel, Field


class Edgar8kAnalysis(BaseModel):
    """Represents the analysis of an 8-K filing.
    
    Attributes:
        item: The 8-K item number being analyzed
        sentiment: Sentiment analysis of the item content
        is_risk_factor: Whether this item represents a risk factor
        impact: Whether this item represents a positive or negative event
        summary: Brief summary of the item's content
    """
    item: str = Field(description="The 8-K item number being analyzed")
    sentiment: str = Field(description="Sentiment analysis of the item content")
    is_risk_factor: bool = Field(description="Whether this item represents a risk factor")
    impact: str = Field(description="Whether this item represents a positive or negative event")
    summary: str = Field(description="Brief summary of the item's content")


class Edgar8kAnalysisResponse(BaseModel):
    """Container for the complete 8-K filing analysis.
    
    Attributes:
        analyses: List of analyses for each item in the filing
        overall_summary: Summary of the filing's overall impact
    """
    analyses: List[Edgar8kAnalysis] = Field(description="List of analyses for each item")
    overall_summary: str = Field(description="Summary of the filing's overall impact") 