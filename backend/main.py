"""Main FastAPI application for Research Assistant."""
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import contextlib
from src.db.database import init_db
from src.api.routes import (
    health_check,
    create_conversation_endpoint,
    get_conversation_endpoint,
    query_endpoint
)
from src.api.auth_routes import register_user, login_user, google_login
from src.api.auth_middleware import get_current_user
from src.models.schemas import (
    QueryRequest,
    QueryResponse,
    ConversationResponse,
    CreateConversationResponse,
    HealthResponse,
    UserCreate,
    UserLogin,
    GoogleLogin,
    TokenResponse,
    UserResponse
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    yield
    # Shutdown logic (if any)

app = FastAPI(title="Research Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ==================== PUBLIC ENDPOINTS ====================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return await health_check()


@app.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register a new user with email/password."""
    return await register_user(user_data)


@app.post("/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login with email and password."""
    return await login_user(user_data)


@app.post("/auth/google", response_model=TokenResponse)
async def google_auth(user_data: GoogleLogin):
    """Login or register with Google OAuth."""
    return await google_login(user_data)


# ==================== PROTECTED ENDPOINTS ====================

@app.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation_route(current_user: UserResponse = Depends(get_current_user)):
    """Create a new conversation for the authenticated user."""
    return await create_conversation_endpoint(current_user.id)


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation_route(conversation_id: int, current_user: UserResponse = Depends(get_current_user)):
    """Get full conversation with all messages."""
    return await get_conversation_endpoint(conversation_id, current_user.id)


@app.post("/query", response_model=QueryResponse)
async def query_route(req: QueryRequest, current_user: UserResponse = Depends(get_current_user)):
    """
    Process a research query.
    If conversation_id is provided, adds message to that conversation.
    If not, creates a new conversation.
    """
    return await query_endpoint(req, current_user.id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)