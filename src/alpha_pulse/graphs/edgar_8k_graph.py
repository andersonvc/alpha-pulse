"""Graph for analyzing SEC EDGAR 8-K filings."""

from typing import Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from alpha_pulse.agents.edgar_8k_agent import Edgar8kAgent
from alpha_pulse.types.analysis import Edgar8kAnalysis
from alpha_pulse.types.state import Edgar8kState
#from alpha_pulse.utils.state_persistence import load_state, save_state



def setup_edgar_8k_workflow(
    model_name: str = "gpt-4o-mini",
    state_dir: str = "state/edgar_8k"
) -> StateGraph:
    """Set up the workflow for analyzing 8-K filings.
    
    Args:
        model_name: Name of the OpenAI model to use
        state_dir: Directory to store state files
        
    Returns:
        StateGraph: Configured workflow graph
    """
    # Create the agent
    agent = Edgar8kAgent(model_name=model_name)
    
    # Define the graph
    workflow = StateGraph(Edgar8kState)
    
    # Add nodes
    workflow.add_node("analyze_filing", agent)
    #workflow.add_node("save_state", save_state)
    
    # Set the entry point
    workflow.set_entry_point("analyze_filing")
    
    # Add edges
    workflow.add_edge("analyze_filing", "save_state")
    workflow.add_edge("save_state", END)
    
    return workflow


def create_edgar_8k_app(
    model_name: str = "gpt-4o-mini",
    state_dir: str = "state/edgar_8k"
) -> StateGraph:
    """Create a compiled workflow for analyzing 8-K filings.
    
    Args:
        model_name: Name of the OpenAI model to use
        state_dir: Directory to store state files
        
    Returns:
        StateGraph: Compiled workflow graph
    """
    workflow = setup_edgar_8k_workflow(model_name, state_dir)
    return workflow.compile()

