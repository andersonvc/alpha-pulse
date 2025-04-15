"""News sentiment analysis agent for financial news."""

from typing import Any, Dict, List, Optional
import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from alpha_pulse.tools.news_tools import get_recent_news


class NewsSentiment(BaseModel):
    """Represents the sentiment analysis of a single news article.
    
    Attributes:
        title: Title of the news article
        source: Source of the news article
        sentiment: Sentiment analysis result (positive, negative, or neutral)
        category: Content category of the article
    """
    title: str = Field(description="Title of the news article")
    source: str = Field(description="Source of the news article")
    sentiment: str = Field(description="Sentiment analysis: positive, negative, or neutral")
    category: str = Field(description="Category of the content of the article")


class NewsSentimentResponse(BaseModel):
    """Container for a collection of analyzed news articles.
    
    Attributes:
        articles: List of analyzed news articles with their sentiments
    """
    articles: List[NewsSentiment] = Field(description="List of analyzed news articles")


class NewsAgent:
    """Agent for analyzing sentiment of financial news articles.
    
    This agent:
    1. Fetches recent news for a given ticker
    2. Analyzes the sentiment of each article
    3. Categorizes the content of each article
    4. Provides a structured response with analysis results
    """
    
    # Internal prompt for the agent
    INTERNAL_PROMPT = """You are a financial news sentiment analyzer. Your task is to:
    1. Fetch recent news for the given ticker
    2. Analyze the sentiment of each article
    3. Provide a category of the content of the article

    Return the results in a structured format with individual article sentiments and an overall summary."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        """Initialize the NewsAgent with a language model.
        
        Args:
            model: Name of the OpenAI model to use (default: "gpt-4o-mini")
        """
        self.agent = ChatOpenAI(
            model=model, 
            temperature=0
        ).bind_tools(
            [get_recent_news]
        ).with_structured_output(
            NewsSentimentResponse
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.INTERNAL_PROMPT),
            ("human", "Analyze news sentiment for {ticker}")
        ])

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Make the agent callable for use with StateGraph.
        
        Args:
            state: Dictionary containing either:
                - 'ticker': str for direct ticker input
                - 'messages': List[AnyMessage] for MessagesState input
            
        Returns:
            Dict containing the analysis results in MessagesState format
            
        Raises:
            ValueError: If state is invalid or missing required information
        """
        ticker = self._extract_ticker_from_state(state)
        result = await self.analyze_news(ticker)
        return {"messages": [AIMessage(str(result))]}

    def _extract_ticker_from_state(self, state: Dict[str, Any]) -> str:
        """Extract ticker symbol from state dictionary.
        
        Args:
            state: Dictionary containing ticker information
            
        Returns:
            str: Extracted ticker symbol
            
        Raises:
            ValueError: If state is invalid or missing ticker information
        """
        if not isinstance(state, dict):
            raise ValueError("State must be a dictionary")
            
        if 'ticker' in state:
            return state['ticker']
            
        if 'messages' in state and state['messages']:
            last_message = state['messages'][-1]
            if isinstance(last_message, HumanMessage):
                return last_message.content
                
        raise ValueError("State must contain either 'ticker' or 'messages' with a HumanMessage")

    async def analyze_news(self, ticker: str) -> NewsSentimentResponse:
        """Analyze news sentiment for a given ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            NewsSentimentResponse: Structured response with analyzed articles
            
        Raises:
            Exception: If news analysis fails
        """
        try:
            response = await self.agent.ainvoke(
                self.prompt.format_messages(ticker=ticker)
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to analyze news for {ticker}: {str(e)}")
