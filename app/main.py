from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import oauth2, schemas
from app.config import settings
from app.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.database import SessionLocal
from app.redis import redis_client
from app.routers import router

from contextlib import asynccontextmanager

from app.whatsapp_client import client


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.whatsapp_enabled:
        await client.connect()
        try:
            yield
        finally:
            await client.disconnect()
    else:
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(SecurityHeadersMiddleware, production=settings.environment == "production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check():
    checks = {"database": False, "redis": False}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        checks["redis"] = bool(redis_client.ping())
    except Exception:
        pass
    if not all(checks.values()):
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "degraded", "checks": checks})
    return {"status": "ready", "checks": checks}
