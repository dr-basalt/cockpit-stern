import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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


# OAuth callback proxy — routes through our trusted domain to avoid Safe Browsing flags
@app.get("/oauth/callback")
async def oauth_callback_proxy(request: Request):
    """Proxy OAuth callbacks to Nango via our trusted domain."""
    import httpx
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"http://nango:3003/oauth/callback",
            params=params,
            follow_redirects=False,
        )
        if r.status_code in (301, 302, 303, 307, 308):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=r.headers.get("location", "/cockpit"))
        from fastapi.responses import Response
        return Response(content=r.content, status_code=r.status_code, headers=dict(r.headers))


# Obot proxy — expose internal Obot (http://obot:8080) via api-stern-os2.ori3com.cloud/obot/
# This fixes localhost:8080 URLs that can't be reached from a browser
@app.api_route("/obot-proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def obot_proxy(request: Request, path: str):
    """Proxy all requests to Obot internal container."""
    import httpx
    from fastapi.responses import Response

    obot_url = f"http://obot:8080/{path}"
    params = dict(request.query_params)
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length", "transfer-encoding")}

    body = await request.body()

    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        r = await client.request(
            method=request.method,
            url=obot_url,
            params=params,
            headers=headers,
            content=body if body else None,
        )

        # Rewrite Location headers: replace localhost:8080 with our external URL
        resp_headers = dict(r.headers)
        if "location" in resp_headers:
            resp_headers["location"] = resp_headers["location"].replace(
                "http://localhost:8080", "https://api-stern-os2.ori3com.cloud/obot-proxy"
            ).replace(
                "http://obot:8080", "https://api-stern-os2.ori3com.cloud/obot-proxy"
            )

        return Response(
            content=r.content,
            status_code=r.status_code,
            headers=resp_headers,
        )
