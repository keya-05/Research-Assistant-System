from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    question: str
    raw_research: str
    sources: List[str]
    summary: str
    answer: str
    confidence: str       # "high" | "medium" | "low"
    verified: bool
    error: Optional[str]