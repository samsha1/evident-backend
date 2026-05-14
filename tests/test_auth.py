from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.core.database import get_db
from apps.api.src.main import app


@pytest.mark.asyncio
async def test_auth_google_new_user():
    """Test successful Google auth for a new user."""
    # Mock Google verification
    mock_idinfo = {
        "sub": "google_123",
        "email": "test@example.com",
        "name": "Test User"
    }
    
    # Mock DB session
    mock_db = AsyncMock()
    mock_db.add = MagicMock() # add is synchronous in SQLAlchemy
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # Simulate user not found
    mock_db.execute.return_value = mock_result
    
    # Mock the user object returned after commit/refresh
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    
    # We need to mock the refresh behavior or just let it pass
    # Since we use AsyncMock, it will just return a new mock if called
    
    # Override get_db dependency
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("apps.api.src.routers.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/auth/google", json={"id_token": "valid.token.jwt"})
            
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify user was added to DB
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_auth_google_existing_user():
    """Test successful Google auth for an existing user."""
    # Mock Google verification
    mock_idinfo = {
        "sub": "google_123",
        "email": "test@example.com",
        "name": "Test User"
    }
    
    # Mock DB session
    mock_db = AsyncMock()
    mock_db.add = MagicMock() # add is synchronous in SQLAlchemy
    mock_result = MagicMock()
    
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.google_id = "google_123"
    
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    # Override get_db dependency
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("apps.api.src.routers.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/auth/google", json={"id_token": "valid.token.jwt"})
            
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    # Verify user was NOT added to DB (since they exist)
    mock_db.add.assert_not_called()
    mock_db.commit.assert_called_once() # But login time updated
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_auth_google_access_token():
    """Test successful Google auth with an access token."""
    # Mock Google tokeninfo response
    mock_tokeninfo = {
        "sub": "google_456",
        "email": "access@example.com",
        "email_verified": "true"
    }
    
    # Mock DB session
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # New user
    mock_db.execute.return_value = mock_result
    
    # Override get_db dependency
    async def override_get_db():
        yield mock_db
        
    app.dependency_overrides[get_db] = override_get_db
    
    # Mock httpx response
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            
        def json(self):
            return self.json_data
            
    async def mock_get(*args, **kwargs):
        return MockResponse(mock_tokeninfo, 200)
        
    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/auth/google", json={"id_token": "access_token_no_dots"}
            )
            
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    
    # Verify user was added to DB
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # Clean up overrides
    app.dependency_overrides.clear()
