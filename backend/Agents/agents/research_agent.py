from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from Agents.utils.llm import get_llm
from Agents.graph.state import AgentState
from dotenv import load_dotenv

load_dotenv()

search_tool = TavilySearchResults(max_results=5)
llm = get_llm()

def research_agent(state: AgentState) -> AgentState:
    """
    Searches the web for information relevant to the question.
    Extracts raw content and source URLs.
    """
    question = state["question"]

    try:
        results = search_tool.invoke(question)

        raw_parts = []
        sources = []

        for r in results:
            raw_parts.append(r.get("content", ""))
            url = r.get("url", "")
            if url:
                sources.append(url)

        raw_research = "\n\n".join(raw_parts)

        # Use LLM to lightly organize the raw findings
        prompt = f"""You are a research assistant. Given the following raw search results for the question: "{question}", 
organize and extract the most relevant factual information. Do not summarize yet — just clean up and structure the key facts.

Search results:
{raw_research}

Organized findings:"""

        response = llm.invoke([HumanMessage(content=prompt)])
        
        if isinstance(response.content, list):
    # Extract the 'text' field from the first item in the list
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
            "error": f"Research agent failed: {str(e)}",
        }