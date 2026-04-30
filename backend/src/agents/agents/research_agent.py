import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from tavily import TavilyClient
from langchain_core.messages import HumanMessage
from src.agents.utils.llm import get_llm
from src.agents.graph.state import AgentState

# Load env before initializing tools
load_dotenv()

# Initialize tools
search_tool = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
llm = get_llm()

# Exponential backoff: Wait 2s, 4s, 8s... up to 10s between retries
@retry(
    wait=wait_exponential(multiplier=1, min=2, max=10), 
    stop=stop_after_attempt(3),
    reraise=True
)
def safe_search(question: str):
    """Wrapper to retry Tavily search if it fails/throttles."""
    response = search_tool.search(query=question, max_results=5)
    return response.get("results", [])



def research_agent(state: AgentState) -> AgentState:
    question = state["question"]

    try:
        # 1. Search with retry logic
        results = safe_search(question)

        raw_parts = []
        sources = []
        for r in results:
            raw_parts.append(r.get("content", ""))
            url = r.get("url", "")
            if url:
                sources.append(url)

        raw_research = "\n\n".join(raw_parts)

        # 2. LLM Processing
        prompt = f"""You are a research assistant. Given the following raw search results for the question: "{question}", 
organize and extract the most relevant factual information. Do not summarize yet — just clean up and structure the key facts.

Search results:
{raw_research}"""

        # Ensure your LLM initialization in utils/llm.py has max_retries=3
        response = llm.invoke([HumanMessage(content=prompt)])
        
        if isinstance(response.content, list):
            final_content = response.content[0].get("text", "")
        else:
            final_content = response.content

        return {
            "raw_research": final_content,
            "sources": sources,
            "error": None,
        }

    except Exception as e:
        return {
            **state,
            "raw_research": "",
            "sources": [],
            "error": f"Research agent failed after retries: {str(e)}",
        }