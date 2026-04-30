"""Pydantic models for request/response validation."""
from typing import Optional, List
from pydantic import BaseModel, field_validator, EmailStr


# ==================== AUTH MODELS ====================

class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    """Request model for Google OAuth login."""
    token: str  # Google ID token from frontend


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    email: str
    full_name: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    """Response model for JWT tokens."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==================== QUERY MODELS ====================

class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str
    conversation_id: Optional[int] = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Too short (min 5 chars)")
        if len(v) > 2000:
            raise ValueError("Too long (max 2000 chars)")
        return v


# ==================== RESPONSE MODELS ====================

class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str
    sources: List[str]
    confidence: str
    cached: bool = False
    conversation_id: int
    message_id: int


class ConversationResponse(BaseModel):
    """Response model for conversation endpoint."""
    id: int
    created_at: str
    updated_at: str
    messages: List


class CreateConversationResponse(BaseModel):
    """Response model for create conversation endpoint."""
    conversation_id: int


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    version: str
