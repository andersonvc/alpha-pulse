"""Agent for parsing x99 supplemental text."""
import json
from typing import Dict, List, Optional
import logging
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
import asyncio


system_prompt = """
    You are an expert at parsing SEC ex99 supplemental text. The provided records has numerous formatting and structure errors. 
    Your job is to preserve the information, but restructure the text in a way that is easy for LLMs to understand. This record
    may contain multiple sections, charts, and tables.
"""


class AgentEX99Parser:
    """Agent for parsing ex99 supplemental text.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        """Initialize the AgentEX99Parser.
        
        Args:
            model_name: Name of the OpenAI model to use
        """
        self.model = ChatOpenAI(model=model_name, temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Text: {raw_text}")
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
            self._extract_items(filing.raw_ex99_texts)
            for filing in state.filingEntries
            if filing.raw_ex99_texts
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update filings with results
        for filing, result in zip(state.filingEntries, results):
            if isinstance(result, Exception):
                logging.error(f"Error processing filing: {str(result)}")
                continue
            filing.parsed_ex99 = result
        
        return state
    
    async def _extract_items(self, raw_text: str) -> str:
        """Extract specified items from raw text using an LLM.
        
        Args:
            raw_text: The raw text of the ex99 supplemental text
            
        Returns:
            str: The formatted text
        """

        # Create the chain
        chain = self.prompt | self.model
        
        # Get the response
        response = await chain.ainvoke({
            "raw_text": raw_text,
        })

        try: 
            return response.content
        except Exception as e:
            logging.error(f"Error parsing LLM response: {str(e)}")
            return ''
