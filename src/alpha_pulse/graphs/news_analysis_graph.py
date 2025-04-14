from langchain_core.messages import AnyMessage
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, HumanMessage

from IPython.display import Image, display

from langgraph.graph import StateGraph, MessagesState, START, END

from alpha_pulse.agents.news_agent import NewsAgent

async def run():
    '''
    class State(TypedDict):
        messages: list[AnyMessage]
        extra_field: int


    def node(state: State):
        messages = state["messages"]
        new_message = AIMessage("Hello!")

        return {"messages": messages + [new_message], "extra_field": 10}


    from langgraph.graph import StateGraph

    graph_builder = StateGraph(State)
    graph_builder.add_node(node)
    graph_builder.set_entry_point("node")
    graph = graph_builder.compile()  

    img =  Image(graph.get_graph().draw_mermaid_png())
    with open("image.png", "wb") as png:
        png.write(img.data)
    
    from langchain_core.messages import HumanMessage

    result = graph.invoke({"messages": [HumanMessage("Hi")]})
    print(result)
    '''

    workflow = StateGraph(MessagesState)
    workflow.add_node("news_agent", NewsAgent())
    workflow.add_edge(START, "news_agent")
    workflow.add_edge("news_agent", END)

    compiled_graph = workflow.compile()
    
    img =  Image(compiled_graph.get_graph().draw_mermaid_png())
    with open("image.png", "wb") as png:
        png.write(img.data)
    
    # Initialize state with a message containing the ticker
    initial_state = {"messages": [HumanMessage("TSLA")]}
    result = await compiled_graph.ainvoke(initial_state)
    print(result)

