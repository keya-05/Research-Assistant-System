from langgraph.graph import StateGraph, END
from graph.state import AgentState
from agents.research_agent import research_agent
from agents.summarization_agent import summarization_agent
from agents.verification_agent import verification_agent

def build_workflow() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("research", research_agent)
    graph.add_node("summarize", summarization_agent)
    graph.add_node("verify", verification_agent)

    # Define edges (linear pipeline)
    graph.set_entry_point("research")
    graph.add_edge("research", "summarize")
    graph.add_edge("summarize", "verify")
    graph.add_edge("verify", END)

    return graph.compile()

# Compile once at import time
workflow = build_workflow()