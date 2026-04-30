"""Authentication routes for Google OAuth only."""
import logging
from fastapi import HTTPException, status
from src.models.schemas import GoogleLogin, TokenResponse, UserResponse
from src.db.database import (
    create_user, get_user_by_id, get_user_by_google_id
)
from src.services.auth_service import (
    create_access_token,
    decode_access_token
)
from src.services.google_auth_service import verify_google_token

logger = logging.getLogger(__name__)


async def google_login(user_data: GoogleLogin) -> TokenResponse:
    """Authenticate or register user with Google OAuth."""
    # Verify Google token
    google_info = verify_google_token(user_data.token)
    if not google_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )
    
    email = google_info["email"]
    google_id = google_info["sub"]
    full_name = google_info.get("name")
    
    # Check if user exists by Google ID
    user = await get_user_by_google_id(google_id)
    
    if not user:
        # Create new Google user
        user_id = await create_user(
            email=email,
            full_name=full_name,
            google_id=google_id
        )
        user = await get_user_by_id(user_id)
        logger.info(f"New Google user created: {email}")
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user["id"]), "email": user["email"]})
    
    logger.info(f"Google user logged in: {email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user)
    )


async def get_current_user_from_token(token: str) -> UserResponse:
    """Get current user from JWT token."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = await get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserResponse(**user)
