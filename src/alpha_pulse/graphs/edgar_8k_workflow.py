from langgraph.graph import StateGraph, END, START


from IPython.display import Image

from alpha_pulse.agents.edgar.agent_8k_parser import Agent8KParser
from alpha_pulse.agents.edgar.agent_8k_801_analyzer import Agent8KAnalyzer_801
from alpha_pulse.types.edgar8k import State8K
from alpha_pulse.types.edgar8k.item_8k_801 import Item8K_801


def compile_workflow(draw_mermaid: bool = False):
    workflow = StateGraph(State8K)

    workflow.add_node("8k_parser", Agent8KParser())
    workflow.add_node("8k_801_analyzer", Agent8KAnalyzer_801())
    
    workflow.add_edge(START, "8k_parser")
    workflow.add_edge("8k_parser", "8k_801_analyzer")
    workflow.add_edge("8k_801_analyzer", END)

    workflow.set_entry_point("8k_parser")
    
    # Compile the workflow before invoking
    compiled_workflow = workflow.compile()

    if draw_mermaid:
        img =  Image(compiled_workflow.get_graph().draw_mermaid_png())
        with open("8k_parser_workflow.png", "wb") as png:
            png.write(img.data)

    return compiled_workflow

async def run_workflow(state: State8K):
    # Ensure state has parsed_items initialized
    if not hasattr(state, 'parsed_items') or state.parsed_items is None:
        state.parsed_items = {}
    
    workflow = compile_workflow()
    result = await workflow.ainvoke(state)
    
    # Convert result back to State8K
    if not isinstance(result, State8K):
        result = State8K(**result)
    
    return result

if __name__ == "__main__":
    compile_workflow(draw_mermaid=True)