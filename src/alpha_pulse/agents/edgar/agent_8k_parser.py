"""Agent for parsing 8-K filing text and separating items."""

import json
import logging
from typing import Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from alpha_pulse.types.edgar8k import BaseItem8K
from alpha_pulse.types.edgar8k import State8K


DEFAULT_SYSTEM_PROMPT = """\
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
    """Agent for parsing 8-K filing text and extracting item sections."""

    def __init__(self, model: Optional[ChatOpenAI] = None, prompt_template: Optional[ChatPromptTemplate] = None):
        """Initialize the parser with model and prompt."""
        self.model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = prompt_template or ChatPromptTemplate.from_messages([
            ("system", DEFAULT_SYSTEM_PROMPT),
            ("human", "Raw text: {raw_text}\\nitems: {items}")
        ])

    def _parse_llm_response(self, content: str) -> Dict[str, str]:
        """Safely parse the LLM JSON response."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {content}")
            raise ValueError("Invalid JSON response from LLM") from e

    async def _invoke_llm(self, raw_text: str, items: list) -> Dict[str, str]:
        """Run the LLM on the provided inputs and return parsed item content."""
        chain = self.prompt | self.model
        response: AIMessage = await chain.ainvoke({
            "raw_text": raw_text,
            "items": items
        })
        return self._parse_llm_response(response.content)

    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        parsed_items = await self._invoke_llm(state.raw_text, state.items)
        for k, v in parsed_items.items():
            state.parsed_items[k] = BaseItem8K(parsed_text=v)
        return state