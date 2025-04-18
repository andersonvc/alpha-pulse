"""Agent for parsing 8-K filing text and separating items."""
import json
import logging
from typing import Dict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from alpha_pulse.types.simple8k import SimpleState8K, Simple8KItem_801
from alpha_pulse.agents.base_agent import BaseAgent


SYSTEM_PROMPT = """
You are an expert in financial disclosures. Analyze the following text from an SEC 8-K filing under Item 8.01: "Other Events".

Based on the disclosure, extract and answer the questions into the following fields. Your answers must be accurate and concise. Return only the values requested, no explanations.

Text:
\"\"\"{parsed_text}\"\"\"

Return a result in a structured format with the following fields:

# Event Classification
- event_type (choose from: M&A, Dividend, Stock Split, Share Repurchase, Earnings Update, Financial Guidance, Restatement, Legal Action, Regulatory Update, Settlement, Compliance Notice, Product Launch, Product Recall, Cybersecurity Incident, Operational Disruption, Plant Closure, Leadership Commentary, Governance Update, Joint Venture, Market Entry/Exit, Strategic Restructuring, Investor Communication, Environmental Impact, Public Response, Other)
- sentiment (what is the overall financial sentiment of the event? choose from: positive, negative, neutral)
- event_summary (a short summary of the event)
- most_relevant_takeaway (a short summary of the most relevant takeaway from the event)
- stock_price_impact (will event impact stock price? true/false)
- stock_price_impact_reasoning (explain the reasoning behind the expected impact)

# Materiality Assessment
- is_material (Does this event have a material impact on the company's financial statements? true/false)
- is_related_to_prior (Does this event relate to prior disclosures? true/false)

# Impact Analysis
- is_financial_impact (Does this event have a financial impact? true/false)
- is_operational_impact (Does this event have an operational impact? true/false)
- is_market_reaction_expected (Is a market reaction expected? true/false)

# Timing and Context
- is_recent_event (Is this event recent? true/false)
- unexpected_timing (Is the timing of this event unexpected? true/false)

# Strategic Context
- list_of_mentioned_companies (commas separated list of company names mentioned in the event)
- list_of_keywords (commas separated list of relevant keywords from the event)
- strategic_signal (Is this event a strategic signal? true/false)
- priority_shift (Has the company's priority shifted? true/false)
"""


class Simple8KAnalyzer_801:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(Simple8KItem_801)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Parsed text: {parsed_text}")
        ])

    
    async def __call__(self, state: SimpleState8K) -> SimpleState8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        parsed_text = state.parsed_items["8.01"].parsed_text
        result: Simple8KItem_801 = await chain.ainvoke({
            "parsed_text": parsed_text
        })
        result.parsed_text = parsed_text
        state.parsed_items["8.01"] = result

        return state
