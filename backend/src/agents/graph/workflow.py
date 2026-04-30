from langgraph.graph import StateGraph, END
from src.agents.graph.state import AgentState
from src.agents.agents.research_agent import research_agent
from src.agents.agents.summarization_agent import summarization_agent
from src.agents.agents.verification_agent import verification_agent

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

# 'app' — used by backend/agents.py (from Agents.graph.workflow import app)
app = build_workflow()

# 'workflow' — used by Agents/main.py and langgraph.json
workflow = app
