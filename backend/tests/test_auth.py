import pytest
from fastapi.testclient import TestClient
from datetime import timedelta
import sys
import os

# Ensure backend directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from src.services.auth_service import create_access_token

client = TestClient(app)

MOCK_USER = {
    "id": 1,
    "email": "test@example.com",
    "full_name": "Test User",
    "google_id": "google-123",
    "created_at": "2023-01-01T00:00:00"
}

@pytest.fixture
def mock_get_user(monkeypatch):
    async def mock_get_user_by_id(user_id: int):
        if user_id == 1:
            return MOCK_USER
        return None
    
    # We patch it where it is used. It is imported and used in auth_routes.py
    monkeypatch.setattr("src.api.auth_routes.get_user_by_id", mock_get_user_by_id)
    return mock_get_user_by_id

def test_auth_me_valid_token(mock_get_user):
    token = create_access_token(data={"sub": "1", "email": "test@example.com"})
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["email"] == "test@example.com"

def test_auth_me_missing_header():
    response = client.get("/auth/me")
    assert response.status_code == 401

def test_auth_me_invalid_token():
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_auth_me_expired_token(mock_get_user):
    token = create_access_token(
        data={"sub": "1", "email": "test@example.com"}, 
        expires_delta=timedelta(minutes=-10)
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
