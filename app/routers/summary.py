import logging
import os
import httpx
import asyncio
from app.database import SessionLocal
from app.models import Agent
from app.auth import verify_token
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Depends, APIRouter, Request
from dotenv import load_dotenv


load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/agents-summary",
    tags=["summary"],
)

logger = logging.getLogger(__name__)

# Simple in-memory cache for summaries to avoid redundant API calls
summary_cache = {}


async def generate_summary(status):
    prompt = f"Agent status: {status}. Give a one line health summary."
    if status in summary_cache:
        return summary_cache[status]
    else:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-3.5-turbo",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )

        result = response.json()["choices"][0]["message"]["content"]
        summary_cache[status] = result
        return result


@router.get("/")
@limiter.limit("10/minute")
async def get_agents_summary(request: Request, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        agents = db.query(Agent).all()
        logger.info("Generating summaries for %s agents", len(agents))

        summaries = await asyncio.gather(
            *[generate_summary(agent.status) for agent in agents],
            return_exceptions=True
        )

        result = []
        for agent, summary in zip(agents, summaries):
            if isinstance(summary, Exception):
                logger.exception("Failed summary for agent %s", agent.name)
                summary = f"Error generating summary: {summary}"
            result.append({
                "name": agent.name,
                "status": agent.status,
                "summary": summary,
            })

        return result
    finally:
        db.close()
