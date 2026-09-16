from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.problem_details import install_exception_handlers
from app.db.session import engine
from app.routers.analytics import router as analytics_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.employees import router as employees_router
from app.routers.exports import router as exports_router
from app.routers.hierarchy import router as hierarchy_router
from app.routers.imports import router as imports_router
from app.routers.search import router as search_router

# The interactive docs are a development affordance, not something the
# deployed app should publish: they enumerate every route, parameter and
# schema for an unauthenticated reader. Disabled outside development.
_IS_PRODUCTION = settings.ENVIRONMENT.lower() in {"production", "prod"}

app = FastAPI(
    title="Employee Hierarchy API",
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    # Never `*`: with `allow_credentials=True` the browser rejects a
    # wildcard anyway, and `settings` validates the pair (see config.py).
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The SPA and the API share an origin, so the access token in the SPA's
# localStorage is exactly as reachable as any script the page will run.
# That makes these headers load-bearing rather than decorative: the CSP is
# what stops an injected script from being the thing that reads it.
_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        # Vite emits hashed JS/CSS assets; no inline <script> is used.
        "script-src 'self'; "
        # Tailwind's runtime injects a <style> element.
        "style-src 'self' 'unsafe-inline'; "
        # Gravatar, plus any https avatar override.
        "img-src 'self' https: data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # No feature here needs any of them.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
}


@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    if _IS_PRODUCTION:
        # Only meaningful over TLS, and Cloud Run terminates TLS for us.
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


install_exception_handlers(app)


# Route precedence (§3.3): /api/v1/* first, then FastAPI's own /docs,
# /redoc and /openapi.json, then /assets/*, then everything else falls
# back to index.html so client-side routes survive a refresh.
@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(hierarchy_router)
app.include_router(imports_router)
app.include_router(exports_router)
app.include_router(analytics_router)
app.include_router(search_router)
app.include_router(audit_router)


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

# Only wired up once the SPA has actually been built into ./static (the
# production image always has it; local `uv run` without a build won't).
if INDEX_HTML.is_file():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        # This route is last, so it catches anything the routers above did
        # not claim - including misspelled and removed API paths. Returning
        # index.html for those would answer a broken API call with `200 OK`
        # and a page of HTML, which a client can only fail to parse. An
        # unmatched /api/ path is a 404, the same as it is without the SPA.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
