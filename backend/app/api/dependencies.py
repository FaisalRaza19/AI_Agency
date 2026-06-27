from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.core.auth import verify_token
from app.models import User

# Standard HTTP Authorization Header Bearer token parser
security_bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts, decodes, and validates the JWT authorization token.
    Returns the authenticated User object from database.
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token or session has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    email: str = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is invalid: missing subject claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from PostgreSQL
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists in UABE registry.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been suspended by Master Owner.",
        )

    return user

async def get_current_owner(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    RBAC dependency protecting Owner-only admin endpoints (e.g. env configurations).
    Explicitly raises 403 Forbidden for sub-owners / operators.
    """
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Action requires Master Owner credentials."
        )
    return current_user

async def get_current_operator(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    RBAC dependency protecting Operator-level business execution endpoints.
    Allows both Owners and Operators (Sub-owners) to access.
    """
    if current_user.role not in ["owner", "operator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Action requires operator credentials."
        )
    return current_user
