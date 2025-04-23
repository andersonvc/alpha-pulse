"""Agent for parsing 8-K filing text and separating items."""
import json
import logging
from typing import Dict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from alpha_pulse.types.edgar8k import BaseItem8K
from alpha_pulse.types.edgar8k import State8K


SYSTEM_PROMPT = """
    You are an expert at parsing SEC 8-K filings.
    Your task is to analyze the raw text of an 8-K filing and separate out the text associated with each item in the provided "items" list.
    
    When parsing a filing:
    1. Extract the content for each Item
    2. Fix any text formatting issues (e.g. words and sentences may be missing whitespace, etc.)
    3. Ensure all content is properly attributed to its Item
    4. Return the content as a JSON string with the following example format (key is the item number):
        {{
            "1.01": "content for item 1.01",
            "2.03": "content for item 2.03"
        }}

    IMPORTANT: Your response must be a valid JSON string with no additional text or explanation.
    Be thorough and accurate in your parsing, do not include irrelevant text.
"""


class Agent8KParser:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Raw text: {raw_text}\nitems: {items}")
        ])
    
    
    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        # Parse the JSON response from the message content
        try:
            resp: AIMessage = await chain.ainvoke({
                "raw_text": state.raw_text,
                "items": state.items
            })

            resp = json.loads(resp.content)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {resp.content}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")

        for k,v in resp.items():
            state.parsed_items[k] = BaseItem8K(parsed_text=v)
        return state
