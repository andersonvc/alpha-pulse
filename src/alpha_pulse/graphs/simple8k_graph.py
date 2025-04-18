# Simple 8K workflow

from langgraph.graph import StateGraph, END, START

from alpha_pulse.agents.edgar.simple_8k_parser import Simple8KParser
from alpha_pulse.agents.edgar.simple_8k_801_analyzer import Simple8KAnalyzer_801
from alpha_pulse.types.simple8k import SimpleState8K

async def run_workflow(state: SimpleState8K):
    # Ensure state has parsed_items initialized
    if not hasattr(state, 'parsed_items') or state.parsed_items is None:
        state.parsed_items = {}
    
    workflow = StateGraph(SimpleState8K)

    workflow.add_node("simple_8k_parser", Simple8KParser())
    workflow.add_node("simple_8k_801_analyzer", Simple8KAnalyzer_801())
    
    workflow.add_edge(START, "simple_8k_parser")
    workflow.add_edge("simple_8k_parser", "simple_8k_801_analyzer")
    workflow.add_edge("simple_8k_801_analyzer", END)

    workflow.set_entry_point("simple_8k_parser")
    
    # Compile the workflow before invoking
    compiled_workflow = workflow.compile()
    result = await compiled_workflow.ainvoke(state)
    
    # Convert result back to SimpleState8K
    if not isinstance(result, SimpleState8K):
        result = SimpleState8K(**result)
    
    return result