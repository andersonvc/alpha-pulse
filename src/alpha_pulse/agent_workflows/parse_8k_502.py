from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional, List

from alpha_pulse.types.dbtables.parsed_items import Item502Summary
from alpha_pulse.openai_limiter import get_openai_limiter,retry_openai

@retry_openai
async def invoke_openai_safely(chain, text: str):
    async with get_openai_limiter(text):
        return await chain.ainvoke({"parsed_text": text})


class Agent502Summarizer:
    base_prompt = """
    You are an expert in analyzing Item 502 U.S. 8-K SEC financial disclosures.
    
    - category: Provide a 1-4 word category of this document.
    - Create a RoleChange list of people who are newly appointed.
    - Create a RoleChange list of people who were newly removed/demoted.

    {parsed_text}
    """
    
    def __init__(self):
        self.model = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.2
        ).with_structured_output(Item502Summary, method='function_calling')

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.base_prompt),
            ("human", "Parsed text: {parsed_text}")
        ])
    
    def __call__(self, text: str) -> Item502Summary:
        chain = self.prompt | self.model
        result: Item502Summary = chain.invoke({"parsed_text": text})
        return result

    async def ainvoke(self, text: str) -> Item502Summary:
        chain = self.prompt | self.model
        result: Item502Summary = await invoke_openai_safely(chain, text)
        return result

# ---- Define graph state ----
class Item502State(TypedDict):
    text: str
    result: Item502Summary

# ---- Create the async graph ----
async def create_502_graph() -> StateGraph:
    agent = Agent502Summarizer()

    async def node(state: Item502State) -> Item502State:
        result: Item502Summary = await agent.ainvoke(state["text"])
        return {"result": result}

    graph = StateGraph(Item502State)
    graph.add_node("summarizer", node)
    graph.set_entry_point("summarizer")
    graph.add_edge("summarizer", END)
    
    return graph.compile()

# ---- Usage example ----
async def run_502_graph(text: str) -> Item502Summary:
    runnable = await create_502_graph()
    output = await runnable.ainvoke({"text": text})
    return output["result"]