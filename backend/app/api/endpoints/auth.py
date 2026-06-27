from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.config import settings
from app.models import User
from app.core.auth import verify_password, create_access_token, create_refresh_token, verify_token
from app.api.dependencies import get_current_owner, get_current_operator

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic validation schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SecretsResponse(BaseModel):
    database_url: str
    gemini_keys_configured: int
    telegram_bot_token: str

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticates owner/operator credentials and yields access + refresh tokens."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User account has been deactivated."
        )

    # Generate tokens
    token_data = {"sub": user.email, "role": user.role}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(payload: RefreshRequest):
    """Validates refresh token and issues a new access token."""
    decoded = verify_token(payload.refresh_token)
    
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )

    email = decoded.get("sub")
    # Fetch user to verify active status
    async with get_db() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: User account is inactive."
            )

        new_access_token = create_access_token(data={"sub": user.email, "role": user.role})
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_operator)):
    """Stateless logout confirmation endpoint."""
    return {"message": f"Successfully logged out user '{current_user.email}'."}

@router.get("/admin/secrets", response_model=SecretsResponse)
async def view_admin_secrets(current_owner: User = Depends(get_current_owner)):
    """
    Guarded admin endpoint.
    Only users with role='owner' can access. Blocks operators with 403 Forbidden.
    """
    return {
        "database_url": settings.DATABASE_URL,
        "gemini_keys_configured": len(settings.gemini_keys_list),
        "telegram_bot_token": settings.TELEGRAM_BOT_TOKEN
    }
