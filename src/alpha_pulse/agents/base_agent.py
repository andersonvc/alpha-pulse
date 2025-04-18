"""Base agent class for all agents in the system."""

from typing import Any, Dict, Optional, TypeVar, Generic
import logging
import asyncio
from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseAgent(Generic[T], ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0) -> None:
        self.model = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_prompt()),
            ("user", "{input}")
        ])
    
    @abstractmethod
    def _get_prompt(self) -> str:
        """Get the system prompt for the agent."""
        pass
    
    @abstractmethod
    async def _process_item(self, item: Any) -> Any:
        """Process a single item."""
        pass
    
    async def __call__(self, state: T) -> T:
        """Process the state using the agent."""
        logging.info(f"Processing state with {self.__class__.__name__}")
        
        items = getattr(state, "items", [])
        tasks = [self._process_item(item) for item in items if item is not None]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item, result in zip(items, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing item: {str(result)}")
                continue
            setattr(item, "result", result)
        
        return state 