from langchain_core.messages import HumanMessage
from utils.llm import get_llm
from graph.state import AgentState
import json

llm = get_llm(temperature=0.0)

def verification_agent(state: AgentState) -> AgentState:
    """
    Reviews the answer for factual consistency with research.
    Assigns a confidence score and verifies source relevance.
    """
    if state.get("error"):
        # Still return a low-confidence structured output on error
        return {
            **state,
            "confidence": "low",
            "verified": False,
        }

    question = state["question"]
    answer = state.get("answer", "")
    # If answer is a list, join it into a string
    if isinstance(answer, list):
        answer = " ".join([str(i) for i in answer])

    research = state.get("raw_research", "")
    sources = state.get("sources", [])

    prompt = f"""You are a fact-checking agent. Your job is to:
1. Check whether the answer is consistent with the research findings.
2. Identify any unsupported or potentially incorrect claims.
3. Assign a confidence level: "high", "medium", or "low".

Question: {question}

Research findings:
{research}

Answer to verify:
{answer}

Number of sources: {len(sources)}

Respond ONLY in valid JSON with this exact format:
{{
  "is_consistent": true or false,
  "issues": "brief description of any issues, or 'none'",
  "confidence": "high" or "medium" or "low",
  "revised_answer": "improved answer if issues found, otherwise same as original"
}}"""

    try:
        res_content = llm.invoke([HumanMessage(content=prompt)]).content
        
        # Ensure we are dealing with a string before stripping
        if isinstance(res_content, list) and len(res_content) > 0:
            raw = res_content[0].get("text", "")
        else:
            raw = str(res_content)

         # Improved JSON cleaning

        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()


        result = json.loads(raw)

        return {
            **state,
            "answer": result.get("revised_answer", answer),
            "confidence": result.get("confidence", "medium"),
            "verified": result.get("is_consistent", False),
            "error": None # Clear previous non-critical errors if successful
        }
    except Exception as e:
        # Fallback: keep existing answer, set medium confidence
        return {
            **state,
            "confidence": "medium",
            "verified": False,
            "error": f"Verification parsing failed (non-critical): {str(e)}",
        }