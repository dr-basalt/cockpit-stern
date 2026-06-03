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


# Legacy OAuth callback proxy for Nango
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


# MCP OAuth callback — handles the code exchange after user authorizes
@app.get("/mcp/callback")
async def mcp_oauth_callback(request: Request):
    """Handle OAuth callback from remote MCP servers (*.obot.ai).

    Flow: User authorized on Google/Slack/etc → redirected here with ?code=...&state=...
    We exchange the code for an access token via the MCP server's token endpoint.
    """
    import httpx
    import base64
    from fastapi.responses import HTMLResponse

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return HTMLResponse(f"<h2>Erreur OAuth</h2><p>{error}: {request.query_params.get('error_description', '')}</p>")

    if not code or not state:
        return HTMLResponse("<h2>Erreur</h2><p>Parametres manquants (code ou state)</p>")

    # Retrieve pending OAuth data
    from app.api.session import _pending_oauth
    from app.services.token_store import token_store
    pending = _pending_oauth.pop(state, None)
    if not pending:
        return HTMLResponse("<h2>Erreur</h2><p>Session OAuth expiree ou inconnue. Relance la connexion.</p>")

    # Exchange code for token
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                pending["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": pending["redirect_uri"],
                    "client_id": pending["client_id"],
                    "client_secret": pending["client_secret"],
                    "code_verifier": pending["code_verifier"],
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if r.status_code != 200:
                return HTMLResponse(f"<h2>Erreur token exchange</h2><pre>{r.text}</pre>")

            token_data = r.json()
            tool_key = pending["tool_key"]

            # Store token in PostgreSQL (survives restarts)
            await token_store.save(tool_key, {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "token_type": token_data.get("token_type"),
                "expires_in": token_data.get("expires_in"),
                "client_id": pending.get("client_id"),
                "client_secret": pending.get("client_secret"),
                "token_endpoint": pending.get("token_endpoint"),
                "tool_key": tool_key,
            })

            return HTMLResponse(f"""
            <html><body style="font-family:system-ui;max-width:600px;margin:40px auto;text-align:center">
                <h2 style="color:#1D9E75">Connexion reussie !</h2>
                <p><strong>{tool_key}</strong> est maintenant connecte a Stern OS2.</p>
                <p>Tu peux fermer cet onglet.</p>
                <p style="color:#888;font-size:12px">Token expire dans {token_data.get('expires_in', '?')}s</p>
            </body></html>
            """)
    except Exception as e:
        return HTMLResponse(f"<h2>Erreur</h2><pre>{e}</pre>")


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
