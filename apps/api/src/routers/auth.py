from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.api.src.core.database import get_db
from apps.api.src.models.models import User
from apps.api.src.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class AuthRequest(BaseModel):
    id_token: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

@router.post("/auth/google", response_model=AuthResponse, tags=["auth"])
async def auth_google(auth_req: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Exchange Google ID token for a session JWT.
    
    Verifies the Google token, upserts the user in the database,
    and returns a signed JWT for use in subsequent requests.
    """
    try:
        # Verify Google token
        # For development/testing, allow a dummy token
        if auth_req.id_token == "dummy_token" and settings.APP_ENV == "development":
            idinfo = {
                "sub": "dummy_google_id",
                "email": "dummy@example.com",
                "name": "Dummy User"
            }
        else:
            idinfo = id_token.verify_oauth2_token(
                auth_req.id_token, requests.Request(), settings.GOOGLE_CLIENT_ID
            )
            
        google_id = idinfo["sub"]
        email = idinfo["email"]
        name = idinfo.get("name", "")
        
        # Upsert user
        result = await db.execute(select(User).where(User.google_id == google_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                google_id=google_id,
                email=email,
                display_name=name,
                tier="free",
                daily_limit=settings.DEFAULT_DAILY_LIMIT
            )
            db.add(user)
            logger.info(f"Created new user: {email}")
        else:
            user.last_login_at = datetime.now(timezone.utc)
            logger.info(f"User login: {email}")
            
        await db.commit()
        await db.refresh(user)
        
        # Issue JWT
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return AuthResponse(access_token=access_token)
        
    except ValueError as e:
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error in auth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
