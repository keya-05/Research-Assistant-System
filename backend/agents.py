import os, json, re, logging, httpx
from dotenv import load_dotenv
load_dotenv()
import os, logging
from dotenv import load_dotenv
# Import your compiled LangGraph from your Agents folder
from Agents.graph.workflow import app as research_graph

load_dotenv()

logger = logging.getLogger(__name__)
API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL   = "groq/compound-mini"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}



async def run_research_pipeline(question: str) -> dict:
    """
    Connects the FastAPI backend to the LangGraph Multi-Agent system.
    """
    logger.info(f"Starting LangGraph pipeline for: {question}")
    
    # Initialize the State for your graph
    # Ensure these keys match what you defined in your State class in graph/state.py
    initial_state = {
        "messages": [("user", question)],
        "question": question,
        "answer": "",
        "sources": [],
        "confidence": "low"
    }

    try:
        # Run the graph
        # ainvoke is used for async execution
        result = await research_graph.ainvoke(initial_state)
        
        logger.info("LangGraph pipeline completed successfully.")
        
        # Extract data from the final state
        return {
            "answer": result.get("answer", "No answer generated."),
            "sources": result.get("sources", [])[:8],
            "confidence": result.get("confidence", "medium"),
        }

    except Exception as e:
        logger.error(f"LangGraph execution failed: {e}", exc_info=True)
        raise


def extract_json(text: str) -> dict:
    """Try multiple strategies to extract JSON from model output."""
    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strategy 2: strip markdown fences
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Strategy 3: find first {...} block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Strategy 4: model didn't return JSON at all — wrap raw text
    logger.warning("Could not extract JSON, wrapping raw answer")
    return {
        "answer": text,
        "sources": [],
        "confidence": "low"
    }


async def run_research_pipeline(question: str) -> dict:
    system = (
        "You are a research assistant. Answer the question. "
        "Reply ONLY with this JSON, no other text:\n"
        '{"answer":"your answer here","sources":["https://example.com"],"confidence":"high"}'
    )

    try:
        raw = await call_groq(system, question)
    except Exception as e:
        logger.error(f"Groq API call failed: {e}", exc_info=True)
        raise

    data = extract_json(raw)

    confidence = data.get("confidence", "medium")
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"

    return {
        "answer":     data.get("answer", "No answer generated."),
        "sources":    data.get("sources", [])[:8],
        "confidence": confidence,
    }