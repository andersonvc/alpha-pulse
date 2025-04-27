from typing import Literal
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime

SentimentType = Literal['negative','neutral','positive']
ImpactType = Literal['none','minor','major']


class TextSummary(BaseModel):
    category: str = Field(..., description="Category for this document")
    summary_list: str = Field(..., description="Text Statements summarizing info likely to impart stock price")


class TextAnalysis(BaseModel):
    sentiment: SentimentType = Field(..., description="Financial analysts' sentiment on document")
    price_impact: ImpactType = Field(..., description="Degree the stock price will be impacted by info contained in this text")
    is_event_unexpected: bool = Field(..., description="Was the event unexpected?")


class FullAnalysis(TextSummary,TextAnalysis):
    pass

class Analyzed801Text(FullAnalysis):
    cik: str = Field(..., description="CIK of the company")
    filing_date: date = Field(..., description="Filing date of the document")
    item_number: str = Field(..., description="Item number of the document")
    ts: datetime = Field(..., description="Timestamp of the document")

    @field_validator('ts')
    def must_be_timezone_aware(cls, v):
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("event_time must be timezone-aware")
        return v
    
    def to_db_dict(self):
        return self.model_dump()