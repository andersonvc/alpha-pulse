"""Agent for parsing 8-K filing text and separating items."""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar8k.item_8k_502 import Item8K_502
from alpha_pulse.types.edgar8k import State8K

SYSTEM_PROMPT = """
You are a document analysis agent that reads SEC 8-K filings and extracts key governance and leadership change information from Item 5.02.

Your task is to parse Item 5.02 and return structured information about any executive or director changes.

Extract the following fields for each individual change:

<content>
{parsed_text}
</content>

{{
  "individuals": [
    {{
      "name": "Full name of the individual",
      "role": "Position or role (e.g., 'Chief Financial Officer' not 'CFO')",
      "event_type": "One of: resignation, appointment, termination, retirement, election",
      "effective_date": "Date when the change takes effect",
      "reason_for_change": "Explanation for the change",
      "background": "1-2 sentence summary of the individual's background",
      "compensation_details": "1-2 sentence summary of compensation information",
      "board_committee_assignments": "Committee assignments if applicable"
    }}
  ]
}}

Guidelines:
- Include multiple entries if the filing discusses more than one individual
- Normalize roles to full titles (e.g., "Chief Financial Officer" instead of "CFO")
- If any field is not disclosed, use an empty string ("")
- Keep background and compensation details concise (1-2 sentences)
- For event_type, only use the exact values: resignation, appointment, termination, retirement, election
- Do not include any additional text or explanations in the response
"""


class Agent8KAnalyzer_502:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Item8K_502)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Parsed text: {parsed_text}")
        ])

    
    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        if '5.02' in state.parsed_items:
            parsed_text = state.parsed_items["5.02"].parsed_text
            result: Item8K_502 = await chain.ainvoke({
                "parsed_text": parsed_text
            })
            result.item_number = "5.02"

            # Copy all state fields to the result
            result.cik = state.cik
            result.ex99_urls = state.url_ex99
            result.filing_date = state.filing_date
            result.url_8k = state.url_8k
            result.parsed_text = parsed_text
            
            # Ensure url_8k is not None
            if result.url_8k is None:
                result.url_8k = ""
                
            state.parsed_items["5.02"] = result

        return state
