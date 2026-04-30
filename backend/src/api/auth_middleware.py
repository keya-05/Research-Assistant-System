"""Authentication middleware and dependencies for protecting routes."""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.models.schemas import UserResponse
from src.api.auth_routes import get_current_user_from_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """
    Dependency to get the current authenticated user from JWT token.
    Use this in protected routes.
    """
    token = credentials.credentials
    try:
        return await get_current_user_from_token(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserResponse]:
    """
    Optional dependency to get current user if token is provided.
    Returns None if no token or invalid token.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user_from_token(credentials.credentials)
    except HTTPException:
        return None
