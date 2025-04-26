"""Workflow for processing 8-K filings."""

import logging
from pathlib import Path
from typing import Optional

from langgraph.graph import StateGraph, END, START
from IPython.display import Image

from alpha_pulse.agents.edgar.agent_8k_parser import Agent8KParser
from alpha_pulse.agents.edgar.agent_8k_801_analyzer import Agent8KAnalyzer_801
from alpha_pulse.agents.edgar.agent_8k_502_analyzer import Agent8KAnalyzer_502
from alpha_pulse.types.edgar8k import State8K
from alpha_pulse.types.edgar8k.item_8k_801 import Item8K_801
from alpha_pulse.types.edgar8k.item_8k_502 import Item8K_502

def compile_workflow(draw_mermaid: bool = False, output_path: Optional[Path] = None) -> StateGraph:
    """Compile the 8-K processing workflow.
    
    Args:
        draw_mermaid: Whether to generate a Mermaid diagram
        output_path: Path to save the Mermaid diagram (if draw_mermaid is True)
        
    Returns:
        Compiled workflow graph
    """
    # Initialize workflow
    workflow = StateGraph(State8K)
    
    # Add nodes
    workflow.add_node("8k_parser", Agent8KParser())
    workflow.add_node("8k_801_analyzer", Agent8KAnalyzer_801())
    workflow.add_node("8k_502_analyzer", Agent8KAnalyzer_502())
    
    # Add edges
    workflow.add_edge(START, "8k_parser")
    
    # Add conditional edges based on item type
    def route_by_item_type(state: State8K) -> str:
        if state.items == "8.01":
            return "8k_801_analyzer"
        elif state.items == "5.02":
            return "8k_502_analyzer"
        return END
    
    workflow.add_conditional_edges(
        "8k_parser",
        route_by_item_type
    )
    
    workflow.add_edge("8k_801_analyzer", END)
    workflow.add_edge("8k_502_analyzer", END)
    
    # Set entry point
    workflow.set_entry_point("8k_parser")
    
    # Compile workflow
    compiled_workflow = workflow.compile()
    
    # Generate diagram if requested
    if draw_mermaid:
        try:
            img = Image(compiled_workflow.get_graph().draw_mermaid_png())
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as png:
                    png.write(img.data)
            else:
                with open("8k_parser_workflow.png", "wb") as png:
                    png.write(img.data)
        except Exception as e:
            logging.error(f"Failed to generate Mermaid diagram: {str(e)}")
    
    return compiled_workflow

async def run_workflow(state: State8K) -> State8K:
    """Run the 8-K processing workflow.
    
    Args:
        state: Initial state for the workflow
        
    Returns:
        Processed state
    """
    # Ensure state has parsed_items initialized
    if not hasattr(state, 'parsed_items') or state.parsed_items is None:
        state.parsed_items = {}
    
    # Run workflow
    workflow = compile_workflow()
    result = await workflow.ainvoke(state)
    
    # Convert result back to State8K if needed
    if not isinstance(result, State8K):
        result = State8K(**result)
    
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    compile_workflow(draw_mermaid=True)