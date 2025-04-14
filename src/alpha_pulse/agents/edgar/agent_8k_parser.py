"""Agent for parsing 8-K filing text and separating items."""
import json
from typing import Dict, List, Optional
import logging
import asyncio
from pydantic import BaseModel, Field

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain.tools import tool

from alpha_pulse.types.edgar import Edgar8kFilingData
from alpha_pulse.types.state import Edgar8kState
from alpha_pulse.agents.edgar.agent_ex99_parser import AgentEX99Parser
from alpha_pulse.agents.edgar.agent_8k_analyzer import Agent8kAnalyzer
class Edgar8kState(BaseModel):
    """State for the 8-K parser agent.
    
    Attributes:
        ticker: Ticker to process
        filingEntries: List of Edgar8kFilingData objects
    """
    ticker: str = Field(..., description="The ticker of the company to process")
    filingEntries: Optional[List[Edgar8kFilingData]] = Field(None, description="List of the 8-K filing data to process")
    #parsedFilings: Optional[List[Dict[str, str]]] = Field(None, description="Dictionary of parsed filings")

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


class Agent8kParser:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialize the Agent8kParser.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model = ChatOpenAI(model=model_name, temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Raw text: {raw_text}\nItem types: {item_types}")
        ])
    
    async def __call__(self, state: Edgar8kState) -> Edgar8kState:
        """Process each filing entry and extract item sections.
        
        Args:
            state: Current state containing filing entries
            
        Returns:
            Edgar8kState: Updated state with parsed items
        """
        logging.info(f"Processing {len(state.filingEntries)} filings")
        
        # Process all filings concurrently
        tasks = [
            self._extract_items(filing.raw_text, filing.item_type)
            for filing in state.filingEntries
            if filing.item_type and filing.raw_text
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update filings with results
        for filing, result in zip(state.filingEntries, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing filing: {str(result)}")
                continue
            filing.parsed_8k = result
        
        return state
    
    async def _extract_items(self, raw_text: str, item_types: List[str]) -> Dict[str, str]:
        """Extract specified items from raw text using an LLM.
        
        Args:
            raw_text: The raw text of the 8-K filing
            item_types: List of item types to extract
            
        Returns:
            Dict[str, str]: Dictionary mapping item numbers to their content
        """

        # short circut solution if only one item exists 
        if len(item_types) == 1:
            return {item_types[0]: raw_text}

        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "raw_text": raw_text,
            "item_types": item_types
        })
        
        # Parse the response into a dictionary
        try:
            parsed_response = json.loads(response.content)
            return parsed_response
            
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return {}


async def run_workflow(ticker: str, limit: int = 3) -> Edgar8kState:
    # initialize the state
    initial_state = Edgar8kState(
        ticker=ticker,
        filingEntries=[],
    )

    from alpha_pulse.tools.edgar import parse_latest_8k_filing_tool

    async def edgar_8k_loader(state: Edgar8kState) -> Edgar8kState:
        ticker = state.ticker
        state.filingEntries = await parse_latest_8k_filing_tool(ticker, limit)
        return state
    
    parse_agent = Agent8kParser()
    ex99_parser = AgentEX99Parser()
    analyze_agent = Agent8kAnalyzer()

    workflow = StateGraph(Edgar8kState)
    
    # Add nodes
    workflow.add_node("edgar_8k_loader", edgar_8k_loader)
    workflow.add_node("parse_agent", parse_agent)
    workflow.add_node("edgar_ex99_parser", ex99_parser)
    workflow.add_node("analyze_agent", analyze_agent)

    # Add edges for completion
    workflow.add_edge("edgar_8k_loader", "parse_agent")
    workflow.add_edge("parse_agent", "edgar_ex99_parser")
    workflow.add_edge("edgar_ex99_parser", "analyze_agent")
    workflow.add_edge("analyze_agent", END)

    workflow.set_entry_point("edgar_8k_loader")

    compiled_graph = workflow.compile()
    result = await compiled_graph.ainvoke(initial_state)
    
    # Ensure result is properly converted to Edgar8kState
    if not isinstance(result, Edgar8kState):
        result = Edgar8kState(**result)
    
    return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from alpha_pulse.graphs.edgar_8k_graph import create_edgar_8k_app
    async def main():
        
        ticker = "TRNR"
        
        ## Run the parser
        final_state: Edgar8kState = await run_workflow(ticker, limit=1)
        for filing in final_state.filingEntries:
            print(filing.parsed_8k)

    
    # Run the async main function
    asyncio.run(main()) 