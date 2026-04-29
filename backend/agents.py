import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Import the compiled LangGraph workflow from the Agents folder
from Agents.graph.workflow import app as research_graph


async def process_query(question: str) -> dict:
    """
    Connects the FastAPI backend to the LangGraph Multi-Agent system.

    Inputs:
        question (str): The user's research question.

    Returns:
        dict with keys:
            - answer (str)
            - sources (list[str])
            - confidence (str)  — "high" | "medium" | "low"
    """
    logger.info(f"Starting LangGraph pipeline for: {question[:80]}")

    # Build the initial AgentState — must match AgentState TypedDict exactly
    initial_state = {
        "question": question,
        "raw_research": "",
        "sources": [],
        "summary": "",
        "answer": "",
        "confidence": "low",
        "verified": False,
        "error": None,
    }

    try:
        # ainvoke for async execution
        result = await research_graph.ainvoke(initial_state)

        logger.info(
            f"LangGraph pipeline completed — "
            f"confidence={result.get('confidence')}, "
            f"sources={len(result.get('sources', []))}"
        )

        # If a hard error occurred with no answer, return a graceful fallback
        if result.get("error") and not result.get("answer"):
            logger.warning(f"Pipeline finished with error state: {result['error']}")
            return {
                "answer": "An error occurred while processing your query. Please try again.",
                "sources": [],
                "confidence": "low",
            }

        # Return only the fields the backend/QueryResponse model needs
        return {
            "answer": result.get("answer", "No answer generated."),
            "sources": result.get("sources", [])[:8],
            "confidence": result.get("confidence", "medium"),
        }

    except Exception as e:
        logger.error(f"LangGraph execution failed: {e}", exc_info=True)
        raise