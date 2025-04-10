# tools/news_tools.py
from pydantic import BaseModel,Field
from typing import Optional,List
import os
from polygon import RESTClient
from datetime import datetime, timedelta
from langchain.tools import tool
from functools import lru_cache

@lru_cache(maxsize=1)
def get_polygon_client():
    return RESTClient(api_key=os.getenv("POLYGON_API_KEY"))


class PolygonNewsEvent(BaseModel):
    """A news event from Polygon"""
    title: Optional[str] = Field(default=None, description="The title of the news event")
    description: Optional[str] = Field(default=None, description="The description of the news event")
    published_at: Optional[datetime] = Field(default=None, description="The date and time the news event was published")
    source: Optional[str] = Field(default=None, description="The source of the news event")
    url: Optional[str] = Field(default=None, description="The url of the news event")
    tickers: Optional[List[str]] = Field(default=None, description="All tickers mentioned in the news event")

class PolygonNewsQueryResponse(BaseModel):
    """A response from the Polygon news API"""
    events: List[PolygonNewsEvent] = Field(default=None, description="The news events from the Polygon news API")


@tool
def get_recent_news(ticker: str, minutes:int=20) -> PolygonNewsQueryResponse:
    """Get news for a given ticker from Polygon.io over past 20 minutes"""
    client = get_polygon_client()
    news = client.get_news(ticker, after=datetime.now() - timedelta(minutes=minutes))

    structured_news = []
    for entry in news.results:
        structured_news.append(PolygonNewsEvent(
            title=entry.title,
            description=entry.description,
            published_at=entry.published_at,
            source=entry.source,
            url=entry.url,
            tickers=entry.tickers)
        )
    return PolygonNewsQueryResponse(events=structured_news)