"""Authentication routes for user registration, login, and Google OAuth."""
import logging
from fastapi import HTTPException, status
from src.models.schemas import UserCreate, UserLogin, GoogleLogin, TokenResponse, UserResponse
from src.db.database import (
    create_user, get_user_by_email, get_user_by_id, get_user_by_google_id
)
from src.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from src.services.google_auth_service import verify_google_token

logger = logging.getLogger(__name__)


async def register_user(user_data: UserCreate) -> TokenResponse:
    """Register a new user with email/password."""
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user (email auto-verified for simplicity)
    hashed_password = get_password_hash(user_data.password)
    user_id = await create_user(
        email=user_data.email, 
        hashed_password=hashed_password, 
        full_name=user_data.full_name
    )
    
    # Get user data for response
    user = await get_user_by_id(user_id)
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user_id), "email": user["email"]})
    
    logger.info(f"User registered: {user_data.email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user)
    )


async def login_user(user_data: UserLogin) -> TokenResponse:
    """Authenticate user with email/password."""
    # Get user by email
    user = await get_user_by_email(user_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not user.get("hashed_password") or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user["id"]), "email": user["email"]})
    
    logger.info(f"User logged in: {user_data.email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            created_at=user["created_at"]
        )
    )


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
        # Check if user exists by email (might have registered with password)
        user = await get_user_by_email(email)
        
        if user:
            # Link Google account to existing user
            # For simplicity, we create a new user - in production you'd link accounts
            logger.info(f"User {email} exists but linking Google OAuth")
        else:
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
