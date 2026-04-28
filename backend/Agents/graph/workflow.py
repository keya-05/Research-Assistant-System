from langgraph.graph import StateGraph, END
from graph.state import AgentState  # Stick to one state class
from agents.research_agent import research_agent
from agents.summarization_agent import summarization_agent
from agents.verification_agent import verification_agent

def build_workflow():
    # 1. Initialize with your defined AgentState
    workflow = StateGraph(AgentState)

    # 2. Register your nodes
    workflow.add_node("research", research_agent)
    workflow.add_node("summarize", summarization_agent)
    workflow.add_node("verify", verification_agent)

    # 3. Define the flow
    workflow.set_entry_point("research")
    workflow.add_edge("research", "summarize")
    workflow.add_edge("summarize", "verify")
    
    # 4. Standard completion
    workflow.add_edge("verify", END)

    return workflow.compile()

# This 'app' is what your FastAPI (agent.py) will import
app = build_workflow()