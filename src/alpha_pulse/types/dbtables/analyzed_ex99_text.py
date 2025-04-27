from typing import Literal
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
SentimentType = Literal['negative','neutral','positive']
ImpactType = Literal['none','minor','major']


class DocSummary(BaseModel):
    category: str = Field(..., description="Category for this document")
    summary_list: str = Field(..., description="Text Statements summarizing info likely to impart stock price")


class DocSentimentSummary(BaseModel):
    sentiment: SentimentType = Field(..., description="Financial analysts' sentiment on document")
    price_impact: ImpactType = Field(..., description="Degree the stock price will be impacted by info contained in this text")
    sentiment_reversal: str = Field(..., description="What event, change would reverse the sentiment")


class DocAnalysis(DocSummary,DocSentimentSummary):
    pass

class AnalyzedEX99Text(DocAnalysis):
    cik: str = Field(..., description="CIK of the company")
    filing_date: date = Field(..., description="Filing date of the document")
    ex99_id: str = Field(..., description="EX99 ID of the document")
    ts: datetime = Field(..., description="Timestamp of the document")
    ex99_url: str = Field(..., description="URL of the EX99 document")

    @field_validator('ts')
    def must_be_timezone_aware(cls, v):
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("event_time must be timezone-aware")
        return v