from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.telegram import router as telegram_router
from app.api.endpoints.telemetry import router as telemetry_router
from app.api.endpoints.resend_webhook import router as email_webhook_router
from app.api.endpoints.billing import router as billing_router
from app.api.endpoints.sandbox import router as sandbox_router
from app.api.endpoints.campaigns import router as campaigns_router
from app.api.endpoints.settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Redis Pub/Sub listener task
    from app.api.endpoints.telemetry import redis_pubsub_listener
    import asyncio
    
    print("--------------------------------------------------")
    print(f"UABE Backend starting up in {settings.ENVIRONMENT} mode...")
    print("--------------------------------------------------")
    
    listener_task = asyncio.create_task(redis_pubsub_listener())
    app.state.telemetry_listener = listener_task
    
    yield
    
    # Shutdown: Cleanly cancel background tasks & engine connections
    print("Cancelling Redis Pub/Sub telemetry listener task...")
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
        
    print("Disposing database connection pool...")
    await engine.dispose()
    print("UABE Backend shut down successfully.")

# Initialize the main FastAPI application using lifespan manager
app = FastAPI(
    title="Universal Autonomous Business Engine (UABE) Core",
    description="The centralized background brain daemon managing agents, campaigns, RAVA, and billing.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS policies to support frontend, WebUI, and Tauri wrappers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri wrapper and local dev run on dynamic origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount security, webhook, billing, and WebSocket stream controllers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(email_webhook_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(sandbox_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Telemetry"])
async def health_check():
    """
    Standard HTTP health check telemetry service.
    Returns status and timestamp.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
