from pydantic import BaseModel
from typing import Optional

class Details8K(BaseModel):
    ticker: str
    cik: str
    filing_date: str
    url_8k_base: str
    url_8k: str
    items: list[str]
    urls_ex99: list[str]

class Parsed8KItem(BaseModel):
    sentiment: int
    companies_mentioned: list[str]

class Parsed8KItem801(Parsed8KItem):
    event_type: str
    summary: str
    impact: str
    is_unexpected: bool
    is_material: bool
    is_reoccurring: bool


class WorkflowState8K(BaseModel):
    details: Details8K
    parsed_8k_items: Optional[dict[str, Parsed8KItem]]
    raw_text: Optional[str]
