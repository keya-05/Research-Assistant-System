"""Google OAuth authentication service."""
import os
from typing import Optional, Dict, Any
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Google ID token and return user info.
    
    Args:
        token: Google ID token from frontend
        
    Returns:
        dict with email, name, picture, sub (Google user ID) or None if invalid
    """
    if not GOOGLE_CLIENT_ID:
        # For development without Google OAuth configured
        # Accept any token and extract mock data (DON'T USE IN PRODUCTION)
        print("WARNING: GOOGLE_CLIENT_ID not set, accepting any token (dev mode only)")
        return {
            "email": "dev@example.com",
            "name": "Development User",
            "picture": None,
            "sub": "dev-user-id"
        }
    
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Check issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return None
            
        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "sub": idinfo.get("sub")  # Google's unique user ID
        }
    except Exception as e:
        print(f"Google token verification failed: {e}")
        return None
