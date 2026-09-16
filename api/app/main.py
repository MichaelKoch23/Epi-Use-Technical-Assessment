from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.problem_details import install_exception_handlers
from app.db.session import engine
from app.routers.auth import router as auth_router
from app.routers.employees import router as employees_router
from app.routers.hierarchy import router as hierarchy_router

app = FastAPI(title="Employee Hierarchy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"

# Only wired up once the SPA has actually been built into ./static (the
# production image always has it; local `uv run` without a build won't).
if INDEX_HTML.is_file():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
