from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app import oauth2, schemas
from app.config import settings
from app.routers import router

from contextlib import asynccontextmanager

from app.whatsapp_client import client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await client.connect()
    yield
    await client.disconnect()


app = FastAPI(lifespan=lifespan)

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
