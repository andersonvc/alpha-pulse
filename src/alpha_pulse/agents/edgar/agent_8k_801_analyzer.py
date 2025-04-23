"""Agent for parsing 8-K filing text and separating items."""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from alpha_pulse.types.edgar8k import Item8K_801
from alpha_pulse.types.edgar8k import State8K

SYSTEM_PROMPT = """
You are an expert in U.S. SEC financial disclosures.

Analyze the Item 8.01 ("Other Events") section below and provide a structured analysis.
Return a structured response with the following fields:

<content>
{parsed_text}
</content>

Required Fields:
1. Event Classification:
   - event_type: Choose one from: M&A, Dividend, Stock Split, Share Repurchase, Earnings Update, Financial Guidance, Restatement, Legal Action, Regulatory Update, Settlement, Compliance Notice, Product Launch, Product Recall, Cybersecurity Incident, Operational Disruption, Plant Closure, Leadership Commentary, Governance Update, Joint Venture, Market Entry/Exit, Strategic Restructuring, Investor Communication, Environmental Impact, Public Response, Other
   - sentiment: Overall financial tone (-1=negative, 0=neutral, 1=positive)
   - event_summary: A concise summary of the event
   - key_takeaway: The most important takeaway from the event

2. Impact Analysis:
   - probable_price_move: Will this event likely impact the stock price? (true/false)
   - price_move_reason: Reasoning for the expected price impact
   - is_financially_material: Does this materially affect financial statements? (true/false)
   - is_operational_impact: Does this affect operations? (true/false)
   - is_related_to_prior: Is this related to prior disclosures? (true/false)

3. Timing and Context:
   - is_recent_event: Did this occur within 30 days of filing? (true/false)
   - unexpected_timing: Was this disclosed outside normal cadence? (true/false)

4. Strategic Context:
   - mentioned_companies: Comma-separated list of legal entity names (no tickers)
   - mentioned_tickers: Comma-separated list of tickers
   - keywords: Up to 10 relevant terms, lowercase, comma-separated
   - strategic_signal: Does this signal strategic change? (true/false)
   - priority_shift_detected: Have company priorities shifted? (true/false)

Guidelines:
- Be precise and factual in your analysis
- Use lowercase true/false for boolean fields
- For sentiment, use -1, 0, or 1
- Keep summaries and takeaways concise but informative
- List companies and keywords without duplicates
- Do not include any additional text or explanations
"""


class Agent8KAnalyzer_801:
    """Agent for parsing 8-K filing text and extracting item sections.
    
    This agent processes each filing entry in the state and extracts the
    specified item sections from the raw text using an LLM.
    """
    
    def __init__(self):
        """Initialize the parser with model and prompt."""
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Item8K_801)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Parsed text: {parsed_text}")
        ])

    
    async def __call__(self, state: State8K) -> State8K:
        """Process the state using the agent."""
        chain = self.prompt | self.model

        if '8.01' in state.parsed_items:
            parsed_text = state.parsed_items["8.01"].parsed_text
            result: Item8K_801 = await chain.ainvoke({
                "parsed_text": parsed_text
            })
            result.item_number = "8.01"

            result.cik = state.cik
            result.ex99_urls = state.url_ex99
            result.filing_date = state.filing_date
            result.url_8k = state.url_8k
            result.parsed_text = parsed_text
            state.parsed_items["8.01"] = result

        return state
