from langchain_core.messages import HumanMessage
from src.agents.utils.llm import get_llm
from src.agents.graph.state import AgentState

llm = get_llm(temperature=0.3)

def summarization_agent(state: AgentState) -> AgentState:
    """
    Takes organized research and produces a concise, coherent answer.
    """
    if state.get("error"):
        return state

    question = state["question"]
    raw_research = state.get("raw_research", "")

    if not raw_research or state.get("error"):
        return {**state, "error": state.get("error") or "No research found to summarize."}

    prompt = f"""You are an expert summarizer. Using the research findings below, write a clear, 
accurate, and concise answer to the user's question.

Question: {question}

Research findings:
{raw_research}

Instructions:
- Write 2–4 paragraphs.
- Stay factual and grounded in the research.
- Do not add information not present in the findings.
- Use plain language.

Answer:"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content_text = response.content if isinstance(response.content, str) else str(response.content)

        return {
            **state,
            "summary": content_text,
            "answer": content_text,
        }

    except Exception as e:
        return {
            **state,
            "error": f"Summarization agent failed: {str(e)}",
        }