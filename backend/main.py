import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from database import init_db, get_cached_query, save_query_response
from agents import process_query

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

class QueryRequest(BaseModel):
    question: str

    @validator("question")
    def validate(cls, v):
        v = v.strip()
        if len(v) < 5:    raise ValueError("Too short (min 5 chars)")
        if len(v) > 2000: raise ValueError("Too long (max 2000 chars)")
        return v

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: str
    cached: bool = False

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    q = req.question.strip()
    logger.info(f"Received question: {q[:80]}")

    # Check cache
    cached = await get_cached_query(q)
    if cached:
        logger.info("Returning cached result")
        return QueryResponse(**cached, cached=True)

    # Run pipeline
    try:
        result = await process_query(q)
        logger.info(f"Pipeline result: confidence={result['confidence']}, sources={len(result['sources'])}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {str(e)}")

    # Save to DB only if it's a real result (not a fallback error)
    if result["confidence"] != "low" or "error occurred" not in result["answer"].lower():
        try:
            await save_query_response(q, result["answer"], result["sources"], result["confidence"])
            logger.info("Saved to database")
        except Exception as e:
            logger.error(f"DB save failed: {e}", exc_info=True)
    else:
        logger.info("Result was a fallback error; skipping database save.")
        # Don't crash the request if DB save fails — still return result

    return QueryResponse(**result)