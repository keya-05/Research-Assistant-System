import os, json, re, logging, httpx
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
API_URL = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL   = "groq/compound-mini"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

async def call_groq(system: str, user: str, max_tokens=1024) -> str:
    if not API_KEY:
        raise ValueError("GROQ_API_KEY is missing from .env")

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    logger.info(f"Calling Groq model: {MODEL}")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(API_URL, headers=HEADERS, json=payload)
        logger.info(f"Groq status: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"].strip()
    logger.info(f"Groq raw response: {content[:300]}")
    return content


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