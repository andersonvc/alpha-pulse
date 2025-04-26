"""Agent for parsing 8-K filing text and separating items."""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar8k import Item8K_201
from alpha_pulse.types.edgar8k import State8K

SYSTEM_PROMPT = """
You are an expert in U.S. SEC financial disclosures.

Analyze the Item 2.01 ("Completion of Acquisition or Disposition of Assets") section below and provide a structured analysis.
Return a structured response with the following fields:

<content>
{parsed_text}
</content>

Required Fields:
1. Transaction Details:
   - transaction_type: Choose one from: Acquisition, Disposition, Merger, Divestiture, Asset Purchase, Asset Sale, Spin-Off, Carve-Out, Business Combination, Other
   - deal_summary: A concise description of the transaction including what was acquired/disposed, value, and counterparties
   - effective_date: Date the transaction was completed (YYYY-MM-DD)
   - consideration_type: Choose one or more from: Cash, Stock, Debt Assumption, Earnout, Mixed, Other
   - counterparties: Comma-separated list of counterparties involved (legal entity names)

2. Financial & Strategic Impact:
   - deal_value_usd: Approximate value of the transaction in USD (numeric, no symbols or commas)
   - is_core_asset: Is the asset involved core to the company’s operations? (true/false)
   - is_financially_material: Does this materially affect financial statements? (true/false)
   - is_operational_impact: Does this affect day-to-day operations? (true/false)
   - strategic_rationale: Brief explanation of strategic reasons for the deal
   - sentiment: Overall financial tone of the transaction (-1=negative, 0=neutral, 1=positive)

3. Market Significance:
   - probable_price_move: Will this likely impact the stock price? (true/false)
   - price_move_reason: Reason for expected market reaction
   - is_related_to_prior: Is this related to previous disclosures? (true/false)

4. Entity & Disclosure Context:
   - mentioned_companies: Comma-separated list of legal entity names (no tickers)
   - mentioned_tickers: Comma-separated list of tickers
   - keywords: Up to 10 relevant terms, lowercase, comma-separated
   - strategic_signal: Does this indicate a shift in long-term strategy? (true/false)
   - priority_shift_detected: Have company priorities shifted due to this transaction? (true/false)

Guidelines:
- Be precise and factual in your analysis
- Use lowercase true/false for boolean fields
- Use -1, 0, or 1 for sentiment
- Summaries and rationales should be concise but meaningful
- Ensure names and keywords are deduplicated
- Do not include any additional text or explanations
"""



class Agent8KAnalyzer_201:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Item8K_201)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Parsed text: {parsed_text}")
        ])

    
    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        if '2.01' in state.parsed_items:
            parsed_text = state.parsed_items["2.01"].parsed_text
            result: Item8K_201 = await chain.ainvoke({
                "parsed_text": parsed_text
            })
            result.item_number = "2.01"

            result.cik = state.cik
            result.ex99_urls = state.url_ex99
            result.filing_date = state.filing_date
            result.url_8k = state.url_8k
            result.parsed_text = parsed_text
            state.parsed_items["2.01"] = result

        return state
