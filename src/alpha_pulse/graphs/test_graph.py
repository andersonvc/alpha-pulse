import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda


class State(TypedDict):
    blah: str
    aggregate: Annotated[dict[str, int], "aggregate", operator.or_]


def a(state: State) -> State:
    print("Running A")
    return {"aggregate": {"a": 1}}

def b(state: State) -> State:
    print("Running B")
    return {"aggregate": {"b": 2}}

def c(state: State) -> State:
    print("Running C")
    return {"aggregate": {"c": 3}}

def d(state: State) -> State:
    print("Running D")
    return {"aggregate": {"d": 4}}


def route_all(state: State) -> list[str]:
    return ["b", "c", "d"]


builder = StateGraph(State)

builder.add_node("a", RunnableLambda(a))
builder.add_node("b", RunnableLambda(b))
builder.add_node("c", RunnableLambda(c))
builder.add_node("d", RunnableLambda(d))
builder.add_node("final", lambda state: state)

builder.set_entry_point("a")
builder.add_conditional_edges("a", route_all)

builder.add_edge("b", "final")
builder.add_edge("c", "final")
builder.add_edge("d", "final")
builder.set_finish_point("final")

graph = builder.compile()

initial_state = {"blah": "hello", "aggregate": {}}
result = graph.invoke(initial_state)
print("\nFinal state:", result)
