from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from alpha_pulse.types.dbtables.analyzed_ex99_text import DocSummary, DocSentimentSummary, DocAnalysis
from alpha_pulse.openai_limiter import get_openai_limiter,retry_openai

class DocState(TypedDict):
    text: str
    combined: DocAnalysis


@retry_openai
async def invoke_openai_safely(chain, text: str):
    async with get_openai_limiter(text):
        return await chain.ainvoke({"parsed_text": text})

class AgentDocSummarizer:

    base_prompt = """
    You are an expert in analyzing U.S. 8-K SEC financial disclosures.
    category: Provide a 1-4 word category of this document.
    summary_list: Compress to text to statements containing info likely to impact stock price. Statements must be <=15 words. Separate statements by '||'
    
    {parsed_text}
    """
    
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o-mini", temperature=.2).with_structured_output(DocSummary)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.base_prompt),
            ("human", "Parsed text: {parsed_text}")
        ])
    
    def __call__(self, text: str)->DocSummary:
        """Process the state using the agent."""
        chain = self.prompt | self.model
        result: DocSummary = chain.invoke({"parsed_text": text})
        return result

    async def ainvoke(self, text: str)->DocSummary:
        """Process the state using the agent."""
        chain = self.prompt | self.model
        result: DocSummary = await invoke_openai_safely(chain, text)
        return result


class AgentSentiment:
    base_prompt = """
    You are an expert in analyzing U.S. SEC financial disclosures.
    Use the following summary to determine market sentiment(negative,neutral,positive) & likely price impact (none,minor,major).
    Also, in 1-10 words identify of what would reverse the sentiment.
    
    {parsed_text}
    """
    
    def __init__(self):
        self.model = ChatOpenAI(model="gpt-4o", temperature=.0).with_structured_output(DocSentimentSummary)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.base_prompt),
            ("human", "Parsed text: {parsed_text}")
        ])
        self.chain = self.prompt | self.model
    
    def __call__(self, text: str)->DocSentimentSummary:
        """Process the state using the agent."""
        return self.chain.invoke({"parsed_text": text})

    async def ainvoke(self, text: str)->DocSentimentSummary:
        """Process the state using the agent."""
        result: DocSentimentSummary = await invoke_openai_safely(self.chain, text)
        return result

# Agents
summary_agent = AgentDocSummarizer()
sentiment_agent = AgentSentiment()

async def create_doc_analysis_graph():
    """Create a graph for analyzing a document."""

    # Single node pipeline
    async def pipeline(state: DocState) -> DocState:
        summary:DocSummary = await summary_agent.ainvoke(state["text"])
        sentiment:DocSentimentSummary = await sentiment_agent.ainvoke(summary.summary_list)
        combined:DocAnalysis = DocAnalysis(**summary.model_dump(), **sentiment.model_dump())
        return {"combined": combined}
    
    # Graph
    graph = StateGraph(DocState)
    graph.add_node("pipeline", pipeline)
    graph.set_entry_point("pipeline")
    graph.add_edge("pipeline", END)
    runnable = graph.compile()
    return runnable

async def run_doc_analysis(text: str) -> DocAnalysis:
    """Run the document analysis graph."""
    runnable = await create_doc_analysis_graph()
    result = await runnable.ainvoke({"text": text})
    return result["combined"]
