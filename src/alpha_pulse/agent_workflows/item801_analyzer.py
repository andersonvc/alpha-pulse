from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from alpha_pulse.types.dbtables.analyzed_801_text import FullAnalysis, TextSummary, TextAnalysis
from alpha_pulse.openai_limiter import get_openai_limiter,retry_openai

class ItemState(TypedDict):
    text: str
    combined: FullAnalysis


@retry_openai
async def invoke_openai_safely(chain, text: str):
    async with get_openai_limiter(text):
        return await chain.ainvoke({"parsed_text": text})


class Agent801Analyzer:

    base_prompt = """
    You are an expert in analyzing the Item 8.01 section of U.S. 8-K SEC financial disclosures.
    category: Provide a 1-4 word category of this document.
    summary_list: Compress to text to statements containing info likely to impact stock price. Statements must be <=15 words. Separate statements by '||'
    
    {parsed_text}
    """
    
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=.2).with_structured_output(TextSummary)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.base_prompt),
            ("human", "Parsed text: {parsed_text}")
        ])
    
    def __call__(self, text: str)->TextSummary:
        """Process the state using the agent."""
        chain = self.prompt | self.model
        return chain.invoke({"parsed_text": text})

    async def ainvoke(self, text: str)->TextSummary:
        """Process the state using the agent."""
        chain = self.prompt | self.model
        result: TextSummary = await invoke_openai_safely(chain, text)
        return result


class Agent801Sentiment:
    base_prompt = """
    You are an expert in analyzing U.S. SEC financial disclosures.
    Use the following summary to determine market sentiment(negative,neutral,positive) & likely price impact (none,minor,major).
    Also give a boolean value for whether the event is unexpected.
    
    {parsed_text}
    """
    
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o", temperature=.0).with_structured_output(TextAnalysis)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.base_prompt),
            ("human", "Parsed text: {parsed_text}")
        ])
        self.chain = self.prompt | self.model
    
    def __call__(self, text: str)->TextAnalysis:
        """Process the state using the agent."""
        return self.chain.invoke({"parsed_text": text})

    async def ainvoke(self, text: str)->TextAnalysis:
        """Process the state using the agent."""
        result: TextAnalysis = await invoke_openai_safely(self.chain, text)
        return result

# Agents
summary_agent = Agent801Analyzer()
sentiment_agent = Agent801Sentiment()

async def create_doc_analysis_graph():
    """Create a graph for analyzing a document."""

    # Single node pipeline
    async def pipeline(state: ItemState) -> ItemState:
        summary:TextSummary = await summary_agent.ainvoke(state["text"])
        sentiment:TextAnalysis = await sentiment_agent.ainvoke(summary.summary_list)
        combined:FullAnalysis = FullAnalysis(**summary.model_dump(), **sentiment.model_dump())
        return {"combined": combined}
    
    # Graph
    graph = StateGraph(ItemState)
    graph.add_node("pipeline", pipeline)
    graph.set_entry_point("pipeline")
    graph.add_edge("pipeline", END)
    runnable = graph.compile()
    return runnable

async def run_item801_analysis(text: str) -> FullAnalysis:
    """Run the document analysis graph."""
    runnable = await create_doc_analysis_graph()
    result = await runnable.ainvoke({"text": text})
    return result["combined"]
