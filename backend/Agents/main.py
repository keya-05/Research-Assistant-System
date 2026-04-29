"""
Standalone entry point for testing the agent pipeline directly.
Run from the backend/ directory:
    python -m Agents.main
or:
    python Agents/main.py  (after adding backend/ to PYTHONPATH)
"""
import sys
import os

# Ensure backend/ is on the path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from Agents.graph.workflow import workflow
from Agents.graph.state import AgentState
from typing import TypedDict


class StructuredResponse(TypedDict):
    answer: str
    sources: list[str]
    confidence: str


def process_query(question: str) -> StructuredResponse:
    """
    Main entry point for the agent system.

    Args:
        question: The user's research question.

    Returns:
        A dict with keys: answer (str), sources (list[str]), confidence (str)
        These match the QueryResponse schema in backend/main.py exactly.
    """
    initial_state: AgentState = {
        "question": question,
        "raw_research": "",
        "sources": [],
        "summary": "",
        "answer": "",
        "confidence": "low",
        "verified": False,
        "error": None,
    }

    final_state = workflow.invoke(initial_state)

    # If a hard error occurred with no answer, return graceful fallback
    if final_state.get("error") and not final_state.get("answer"):
        return {
            "answer": "An error occurred while processing your query. Please try again.",
            "sources": [],
            "confidence": "low",
        }

    return {
        "answer": final_state["answer"],
        "sources": final_state["sources"][:8],
        "confidence": final_state["confidence"],
    }


# Quick local test
if __name__ == "__main__":
    result = process_query("Explain the impact of AI on healthcare")
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])
    print("Confidence:", result["confidence"])