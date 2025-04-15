"""Graph for analyzing SEC EDGAR 8-K filings."""

import asyncio
import logging

from langgraph.graph import StateGraph, END
import pprint
from IPython.display import Image

from alpha_pulse.agents.edgar.agent_8k_parser import Agent8kParser
from alpha_pulse.agents.edgar.agent_ex99_parser import AgentEX99Parser
from alpha_pulse.agents.edgar.agent_8k_analyzer import Agent8kAnalyzer
from alpha_pulse.types.state import Edgar8kState


async def run_workflow(ticker: str, limit: int = 3) -> Edgar8kState:
    # initialize the state
    initial_state = Edgar8kState(
        ticker=ticker,
        filingEntries=[],
    )

    from alpha_pulse.tools.edgar import parse_latest_8k_filing_tool

    async def edgar_8k_loader(state: Edgar8kState) -> Edgar8kState:
        ticker = state.ticker
        state.filingEntries = await parse_latest_8k_filing_tool(ticker, limit)
        return state
    
    parse_agent = Agent8kParser()
    ex99_parser = AgentEX99Parser()
    analyze_agent = Agent8kAnalyzer()

    workflow = StateGraph(Edgar8kState)
    
    # Add nodes
    workflow.add_node("edgar_8k_loader", edgar_8k_loader)
    workflow.add_node("parse_agent", parse_agent)
    workflow.add_node("edgar_ex99_parser", ex99_parser)
    workflow.add_node("analyze_agent", analyze_agent)

    # Add edges for completion
    workflow.add_edge("edgar_8k_loader", "parse_agent")
    workflow.add_edge("parse_agent", "edgar_ex99_parser")
    workflow.add_edge("edgar_ex99_parser", "analyze_agent")
    workflow.add_edge("analyze_agent", END)

    workflow.set_entry_point("edgar_8k_loader")

    compiled_graph = workflow.compile()

    img =  Image(compiled_graph.get_graph().draw_mermaid_png())
    with open("image.png", "wb") as png:
        png.write(img.data)

    result = await compiled_graph.ainvoke(initial_state)
    
    # Ensure result is properly converted to Edgar8kState
    if not isinstance(result, Edgar8kState):
        result = Edgar8kState(**result)
    
    return result


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        
        ticker = "SPGI"
        
        ## Run the parser
        final_state: Edgar8kState = await run_workflow(ticker, limit=1)
        for filing in final_state.filingEntries:
            pprint.pprint(filing.parsed_8k)

    
    # Run the async main function
    asyncio.run(main()) 