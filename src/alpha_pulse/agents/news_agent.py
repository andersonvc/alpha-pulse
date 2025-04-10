from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List
from pydantic import BaseModel,Field

from alpha_pulse.tools.news_tools import get_recent_news


# Pydantic models for structured output
class NewsSentiment(BaseModel):
    title: str = Field(description="Title of the news article")
    source: str = Field(description="Source of the news article")
    sentiment: str = Field(description="Sentiment analysis: positive, negative, or neutral")

class NewsSentimentResponse(BaseModel):
    articles: List[NewsSentiment] = Field(description="List of analyzed news articles")


class NewsAgent:
    # System prompt for the agent
    INTERNAL_PROMPT = """You are a financial news sentiment analyzer. Your task is to:
    1. Fetch recent news for the given ticker
    2. Analyze the sentiment of each article
    3. Provide a summary of the overall sentiment

    Return the results in a structured format with individual article sentiments and an overall summary."""

    def __init__(self, model:str="gpt-4o-mini"):
        self.agent = ChatOpenAI(
            model=model, 
            temperature=0).bind_tools(
                [get_recent_news]
            ).with_structured_output(
                NewsSentimentResponse
            )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.INTERNAL_PROMPT),
            ("human", "Analyze news sentiment for {ticker}")
        ])

    async def analyze_news(self, ticker: str) -> NewsSentimentResponse:
        """
        Analyze news sentiment for a given ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            NewsSentimentResponse: Structured response with analyzed articles and summary
        """
        response = await self.agent.ainvoke(
            self.prompt.format_messages(ticker=ticker)
        )
        return response
