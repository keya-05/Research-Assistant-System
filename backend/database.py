import os, json, logging, asyncpg
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources JSONB NOT NULL DEFAULT '[]',
                confidence VARCHAR(10) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    logger.info("DB ready.")

async def get_cached_query(question: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT answer, sources, confidence FROM queries WHERE question=$1 ORDER BY created_at DESC LIMIT 1",
            question
        )
    if row:
        return {
            "answer": row["answer"],
            "sources": row["sources"] if isinstance(row["sources"], list) else json.loads(row["sources"]),
            "confidence": row["confidence"]
        }
    return None

async def save_query_response(question, answer, sources, confidence):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO queries (question, answer, sources, confidence) VALUES ($1,$2,$3::jsonb,$4)",
            question, answer, json.dumps(sources), confidence
        )