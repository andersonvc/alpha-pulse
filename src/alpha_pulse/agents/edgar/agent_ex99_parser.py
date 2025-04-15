"""Agent for parsing x99 supplemental text."""
import logging

from langchain.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar import Edgar8kFilingData
from alpha_pulse.types.state import Edgar8kState
from alpha_pulse.agents.base_agent import BaseAgent


system_prompt = """
    You are an expert at parsing SEC ex99 supplemental text. The provided records has numerous formatting and structure errors. 
    Your job is to preserve the information, but restructure the text in a way that is easy for LLMs to understand. This record
    may contain multiple sections, charts, and tables.
"""


class AgentEX99Parser(BaseAgent[Edgar8kState]):
    """Agent for parsing ex99 supplemental text.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialize the AgentEX99Parser.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        super().__init__(model_name)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Text: {raw_text}")
        ])
    
    def _get_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return system_prompt
    
    def _get_items_from_state(self, state: Edgar8kState) -> list:
        """Get the filing entries from the state."""
        return state.filingEntries or []
    
    def _should_process_item(self, item: Edgar8kFilingData) -> bool:
        """Determine if a filing should be processed."""
        return item.raw_ex99_texts is not None
    
    async def _process_item(self, filing: Edgar8kFilingData) -> str:
        """Extract specified items from raw text using an LLM.
        
        Args:
            filing: The filing to process
            
        Returns:
            str: The formatted text
        """
        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "raw_text": filing.raw_ex99_texts
        })

        try: 
            return response.content
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return ''
    
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
            filing.parsed_ex99 = result
        return state
