"""API routes for the Research Assistant."""
import logging
from fastapi import HTTPException
from src.models.schemas import (
    QueryRequest,
    QueryResponse,
    ConversationResponse,
    CreateConversationResponse,
    HealthResponse
)
from src.db.database import (
    get_cached_query,
    create_conversation,
    get_conversation,
    add_message_to_conversation
)
from src.services.research_service import process_query

logger = logging.getLogger(__name__)


async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


async def create_conversation_endpoint(user_id: int) -> CreateConversationResponse:
    """Create a new conversation for a user."""
    conversation_id = await create_conversation(user_id)
    return {"conversation_id": conversation_id}


async def get_conversation_endpoint(conversation_id: int, user_id: int) -> ConversationResponse:
    """Get full conversation with all messages."""
    conversation = await get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # TODO: Add user ownership check here
    return conversation


async def query_endpoint(req: QueryRequest, user_id: int) -> QueryResponse:
    """
    Process a research query.
    If conversation_id is provided, adds message to that conversation.
    If not, creates a new conversation.
    """
    q = req.question.strip()
    conversation_id = req.conversation_id
    logger.info(f"Received question: {q[:80]}, conversation_id: {conversation_id}, user_id: {user_id}")

    # Create new conversation if not provided
    if conversation_id is None:
        conversation_id = await create_conversation(user_id)
        logger.info(f"Created new conversation {conversation_id} for user {user_id}")
    
    # Check cache within conversation
    cached = await get_cached_query(q, conversation_id)
    if cached:
        logger.info(f"Returning cached result from conversation {conversation_id}")
        # Add to conversation anyway to maintain message order
        message_id = await add_message_to_conversation(
            conversation_id, q, cached["answer"], cached["sources"], cached["confidence"]
        )
        return QueryResponse(**cached, cached=True, conversation_id=conversation_id, message_id=message_id)

    # Run research pipeline
    try:
        result = await process_query(q)
        logger.info(f"Pipeline result: confidence={result['confidence']}, sources={len(result['sources'])}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {str(e)}")

    # Save to conversation
    try:
        message_id = await add_message_to_conversation(
            conversation_id, q, result["answer"], result["sources"], result["confidence"]
        )
        logger.info(f"Saved to conversation {conversation_id}, message_id: {message_id}")
    except Exception as e:
        logger.error(f"DB save failed: {e}", exc_info=True)
        # Don't crash the request if DB save fails — still return result
        message_id = 0

    return QueryResponse(**result, conversation_id=conversation_id, message_id=message_id)
