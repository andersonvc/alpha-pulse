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

from alpha_pulse.types.edgar import Edgar8kFilingData, Edgar8kFilingAnalysis
from alpha_pulse.types.state import Edgar8kState
from alpha_pulse.agents.edgar.agent_ex99_parser import AgentEX99Parser

class Edgar8kState(BaseModel):
    """State for the 8-K parser agent.
    
    Attributes:
        ticker: Ticker to process
        filingEntries: List of Edgar8kFilingData objects
    """
    ticker: str = Field(..., description="The ticker of the company to process")
    filingEntries: Optional[List[Edgar8kFilingData]] = Field(None, description="List of the 8-K filing data to process")
    filingAnalyses: Optional[List[Edgar8kFilingAnalysis]] = Field(None, description="List of the 8-K filing analyses")
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


class Agent8kAnalyzer:
    """Agent for analyzing 8-K filings.
    
    This agent processes each filing entry in the state and analyzes the 8-K filing.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialize the Agent8kAnalyzer..
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model = ChatOpenAI(model=model_name, temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "8-K Item Dict:\n{parsed_8k}")
        ])
    
    async def __call__(self, state: Edgar8kState) -> Edgar8kState:
        """Process each filing entry and analyze the 8-K filing.
        
        Args:
            state: Current state containing filing entries
            
        Returns:
            Edgar8kState: Updated state with analyzed 8-K filings
        """
        logging.info(f"Processing {len(state.filingEntries)} filings")
        
        # Process all filings concurrently
        tasks = [
            self._analyze_filing(filing.parsed_8k)
            for filing in state.filingEntries
            if filing.parsed_8k
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print('FFFF')
        print(results)
        print('FFFF')
        
        # Update filings with results
        for filing, result in zip(state.filingEntries, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing filing: {str(result)}")
                continue
            filing.parsed_8k = result
        return state
    
    async def _analyze_filing(self, parsed_8k: Edgar8kFilingData) -> Edgar8kFilingData:
        """Analyze a 8-K filing using an LLM.
        
        Args:
            parsed_8k: The parsed 8-K filing
            
        Returns:
            Edgar8kFilingData: The analyzed 8-K filing
        """

        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "parsed_8k": parsed_8k,
        })
        
        # Parse the response into a dictionary
        try:
            parsed_response = json.loads(response.content)
            return parsed_response
            
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return {}
