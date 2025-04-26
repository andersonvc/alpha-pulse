"""Item 2.02 type for 8-K filings."""

from typing import Literal, List, Optional
from pydantic import Field
from alpha_pulse.types.edgar8k.base_item_8k import BaseItem8K


class Item8K_202(BaseItem8K):
    """Represents an analysis of an 8-K Item 2.02 filing."""
    
    earnings_period: str
    revenue_change: Optional[float] = Field(None, description="Percent change in revenue YoY")
    eps_change: Optional[float] = Field(None, description="Percent change in EPS YoY")
    beats_estimates: bool
    financial_highlight: str
    sentiment: int  # -1 = negative, 0 = neutral, 1 = positive
    earnings_summary: str
    key_takeaway: str
    probable_price_move: bool
    price_move_reason: str
    is_financially_material: bool
    guidance_updated: bool
    is_operational_shift: bool
    report_date_within_expected_window: bool
    surprise_announcement: bool
    mentioned_companies: List[str]
    mentioned_tickers: List[str]
    keywords: List[str]
    strategic_shift_detected: bool
    investor_sentiment_signal: bool
    content: str