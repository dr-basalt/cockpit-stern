import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.chat import router as chat_router
from app.api.profile import router as profile_router
from app.api.session import router as session_router
from app.api.ada import router as ada_router
from app.api.design import router as design_router

logging.basicConfig(level=logging.INFO if settings.ENVIRONMENT == "development" else logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Cockpit Stern · {settings.ENVIRONMENT}")
    await init_db()
    from app.services.langfuse_callback import init_langfuse
    init_langfuse()
    from app.services.pattern_detector_task import start_pattern_detector
    start_pattern_detector()
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
app.include_router(ada_router, prefix="/ada", tags=["ada"])
app.include_router(design_router, prefix="/design", tags=["design"])


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
