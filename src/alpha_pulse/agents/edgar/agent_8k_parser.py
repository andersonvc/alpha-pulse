"""Agent for parsing 8-K filing text and separating items."""
import json
from typing import Dict, List, Optional
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar import Edgar8kFilingData
from alpha_pulse.types.state import Edgar8kState
from alpha_pulse.agents.base_agent import BaseAgent

system_prompt = """
    You are an expert at parsing SEC 8-K filings.
    Your task is to analyze the raw text of an 8-K filing and separate out
    the different items in the filing. The expected items are provided in the expected_items field.
    
    When parsing a filing:
    1. Identify each Item section
    2. Extract the content for each Item
    3. Clean up any formatting issues
    4. Ensure all content is properly attributed to its Item
    5. Return the content as a JSON string with the following example format (key is the item number):
        {{
            "1.01": "content for item 1.01",
            "2.03": "content for item 2.03"
        }}

    IMPORTANT: Your response must be a valid JSON string with no additional text or explanation.
    Be thorough and accurate in your parsing.
"""

class Agent8kParser(BaseAgent[Edgar8kState]):
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def _get_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return system_prompt
    
    def _get_items_from_state(self, state: Edgar8kState) -> list:
        """Get the filing entries from the state."""
        return state.filingEntries or []
    
    def _should_process_item(self, item: Edgar8kFilingData) -> bool:
        """Determine if a filing should be processed."""
        return item.item_type is not None and item.raw_text is not None
    
    async def _process_item(self, filing: Edgar8kFilingData) -> Dict[str, str]:
        """Extract specified items from raw text using an LLM.
        
        Args:
            filing: The filing to process
            
        Returns:
            Dict[str, str]: Dictionary mapping item numbers to their content
        """
        # Short circuit solution if only one item exists
        if len(filing.item_type) == 1:
            return {filing.item_type[0]: filing.raw_text}

        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "input": f"Raw text: {filing.raw_text}\nItem types: {filing.item_type}"
        })
        
        # Parse the response into a dictionary
        try:
            return json.loads(response.content)
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return {}
    
    def _update_state_with_results(self, state: Edgar8kState, items: list, results: list) -> Edgar8kState:
        """Update the state with the processing results.
        
        Args:
            state: The current state
            items: The original filings
            results: The processing results
            
        Returns:
            Edgar8kState: The updated state
        """
        for filing, result in zip(items, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing filing: {str(result)}")
                continue
            filing.parsed_8k = result
        return state
