"""Agent for analyzing 8-K filings."""
import json
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel, Field

from alpha_pulse.types.edgar import Edgar8kFilingData
from alpha_pulse.types.state import Edgar8kState
from alpha_pulse.agents.base_agent import BaseAgent

system_prompt = """
    You are an expert at evaluating SEC 8-K filings.
    Your task is to analyze the provided dictionary of items in an 8-K and the items' corresponding text.
    
    When parsing a filing:
    1. For each Item entry in the dictionary, determine whether the event sentiment is positive, negative, or neutral for the company.
    2. For each Item entry in the dictionary, briefly explain why the event is expected, unexpected, or unknown.
    3. For each Item entry in the dictionary, determine whether the event is expected, unexpected, or unknown.
    4. For each Item entry in the dictionary, briefly explain why the event is expected, unexpected, or unknown.
    5. For each Item entry in the dictionary, determine whether the event is material, non-material, or unknown.
    6. For each Item entry in the dictionary, briefly explain why the event is material, non-material, or unknown.
    7. Provide a summary of the events in the 8-K filing.
    8. Provide a list of all other companies that are involved in the events described in the 8-K filing.
    9. Return the results as a JSON string with the following example format (key is the item number):
        {{
            "summary": "summary of the events in the 8-K filing",
            "items": [
                {{
                    "item_number": "item number",
                    "event_sentiment": "positive, negative, or neutral",
                    "event_sentiment_rationale": "rationale for the event sentiment",
                    "event_expected": "expected, unexpected, or unknown",
                    "event_expected_rationale": "rationale for the event being expected or unexpected",
                    "event_material": "material, non-material, or unknown",
                    "event_material_rationale": "rationale for the event being material or non-material"
                }}
            ],
            "related_companies": ["company1", "company2", "company3"]
        }}

    IMPORTANT: Your response must be a valid JSON string with no additional text or explanation.
    Be thorough and accurate in your parsing.
"""

class Agent8kAnalyzer(BaseAgent[Edgar8kState]):
    """Agent for analyzing 8-K filings.
    
    This agent processes each filing entry in the state and analyzes the 8-K filing.
    """
    
    def _get_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return system_prompt
    
    def _get_items_from_state(self, state: Edgar8kState) -> list:
        """Get the filing entries from the state."""
        return state.filingEntries or []
    
    def _should_process_item(self, item: Edgar8kFilingData) -> bool:
        """Determine if a filing should be processed."""
        return item.parsed_8k is not None
    
    async def _process_item(self, filing: Edgar8kFilingData) -> Dict[str, Any]:
        """Analyze a 8-K filing using an LLM.
        
        Args:
            filing: The filing to process
            
        Returns:
            Dict[str, Any]: The analysis results
        """
        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "input": f"{filing.parsed_8k}"
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
