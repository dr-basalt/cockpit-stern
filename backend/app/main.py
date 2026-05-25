import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.chat import router as chat_router
from app.api.profile import router as profile_router
from app.api.session import router as session_router

logging.basicConfig(level=logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Cockpit Stern · {settings.ENVIRONMENT}")
    await init_db()
    yield
    logger.info("Shutting down Cockpit Stern")


app = FastAPI(
    title="Cockpit Stern API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(profile_router, prefix="/api", tags=["profile"])
app.include_router(session_router, prefix="/api", tags=["session"])


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
