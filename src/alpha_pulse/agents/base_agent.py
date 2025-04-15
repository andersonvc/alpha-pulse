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
    """Base class for all agents in the system.
    
    This class provides common functionality for all agents:
    - LLM initialization and configuration
    - Prompt template management
    - Error handling
    - Async processing
    - State management
    
    Subclasses should implement:
    - _process_item: Process a single item
    - _get_prompt: Get the system prompt
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0) -> None:
        """Initialize the base agent.
        
        Args:
            model_name: Name of the OpenAI model to use
            temperature: Temperature for the model (default: 0)
        """
        self.model = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_prompt()),
            ("user", "{input}")
        ])
    
    @abstractmethod
    def _get_prompt(self) -> str:
        """Get the system prompt for the agent.
        
        Returns:
            str: The system prompt
        """
        pass
    
    @abstractmethod
    async def _process_item(self, item: Any) -> Any:
        """Process a single item.
        
        Args:
            item: The item to process
            
        Returns:
            Any: The processed item
        """
        pass
    
    async def __call__(self, state: T) -> T:
        """Process the state using the agent.
        
        Args:
            state: The current state
            
        Returns:
            T: The updated state
        """
        logging.info(f"Processing state with {self.__class__.__name__}")
        
        # Get the items to process from the state
        items = self._get_items_from_state(state)
        
        # Process all items concurrently
        tasks = [
            self._process_item(item)
            for item in items
            if self._should_process_item(item)
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update state with results
        return self._update_state_with_results(state, items, results)
    
    def _get_items_from_state(self, state: T) -> list:
        """Get the items to process from the state.
        
        Args:
            state: The current state
            
        Returns:
            list: The items to process
        """
        # Default implementation - override in subclasses if needed
        return getattr(state, "items", [])
    
    def _should_process_item(self, item: Any) -> bool:
        """Determine if an item should be processed.
        
        Args:
            item: The item to check
            
        Returns:
            bool: True if the item should be processed
        """
        # Default implementation - override in subclasses if needed
        return item is not None
    
    def _update_state_with_results(self, state: T, items: list, results: list) -> T:
        """Update the state with the processing results.
        
        Args:
            state: The current state
            items: The original items
            results: The processing results
            
        Returns:
            T: The updated state
        """
        # Default implementation - override in subclasses if needed
        for item, result in zip(items, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing item: {str(result)}")
                continue
            setattr(item, "result", result)
        return state 