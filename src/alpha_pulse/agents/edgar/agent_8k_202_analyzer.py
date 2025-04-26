"""Agent for parsing 8-K filing text and separating items."""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar8k.item_8k_202 import Item8K_202
from alpha_pulse.types.edgar8k import State8K

SYSTEM_PROMPT = """
You are an expert in U.S. SEC financial disclosures.

Analyze the Item 2.02 ("Results of Operations and Financial Condition") section below and provide a structured analysis.
Return a structured response with the following fields:

<content>
{parsed_text}
</content>

Required Fields:
1. Earnings Summary:
   - earnings_period: Fiscal period covered (e.g., Q1 2025, FY 2024)
   - revenue_change: Percent change in revenue year-over-year (if stated)
   - eps_change: Percent change in earnings per share year-over-year (if stated)
   - beats_estimates: Did the company beat analyst estimates? (true/false)
   - financial_highlight: Key financial metric or outcome emphasized by the company
   - sentiment: Overall financial tone (-1=negative, 0=neutral, 1=positive)
   - earnings_summary: A concise summary of the reported results
   - key_takeaway: The most important takeaway from the earnings release

2. Market Impact:
   - probable_price_move: Will this event likely impact the stock price? (true/false)
   - price_move_reason: Reasoning for the expected price impact
   - is_financially_material: Does this materially affect financial statements? (true/false)
   - guidance_updated: Was forward-looking guidance provided or revised? (true/false)
   - is_operational_shift: Does the filing indicate any operational change? (true/false)

3. Temporal and Contextual Factors:
   - report_date_within_expected_window: Was this disclosed within typical reporting timing? (true/false)
   - surprise_announcement: Was the filing unexpected or outside the scheduled cadence? (true/false)

4. Strategic and Analytical Context:
   - mentioned_companies: Comma-separated list of legal entity names (no tickers)
   - mentioned_tickers: Comma-separated list of tickers
   - keywords: Up to 10 relevant terms, lowercase, comma-separated
   - strategic_shift_detected: Is there evidence of a shift in business direction? (true/false)
   - investor_sentiment_signal: Is there an implied shift in investor perception? (true/false)

Guidelines:
- Be precise and factual in your analysis
- Use lowercase true/false for boolean fields
- For sentiment, use -1, 0, or 1
- Keep summaries and takeaways concise but informative
- List companies and keywords without duplicates
- Do not include any additional text or explanations
"""



class Agent8KAnalyzer_202:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Item8K_202)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Parsed text: {parsed_text}")
        ])

    
    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        if '2.02' in state.parsed_items:
            parsed_text = state.parsed_items["2.02"].parsed_text
            result: Item8K_202 = await chain.ainvoke({
                "parsed_text": parsed_text
            })
            result.item_number = "2.02"

            result.cik = state.cik
            result.ex99_urls = state.url_ex99
            result.filing_date = state.filing_date
            result.url_8k = state.url_8k
            result.parsed_text = parsed_text
            state.parsed_items["2.02"] = result

        return state
