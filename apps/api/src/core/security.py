from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get current user from JWT token.
    
    For now, this is a stub that accepts any token and returns a dummy user ID.
    In Phase 5, this will validate the Google OAuth JWT.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    logger.debug(f"Received token: {token[:10]}...")
    
    # TODO: Implement real JWT validation
    # For now, return a fixed user ID for testing rate limiting
    return "dummy_user_id"
