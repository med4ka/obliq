"""Obliq API entrypoint (FastAPI).

Read-only endpoints in Fase 1 (PRD.md Fase 1 / ARCHITECTURE.md 3). The API reads
from the database only -- never from external sources; that is the pipeline's
job. No auth/rate-limiting yet: deliberately out of scope for Fase 1 (scheduled
for Fase 4, see PROGRESS.md).
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api.routers import auth, macro, stocks, watchlist, yield_curve
from db.connection import get_engine

logger = logging.getLogger(__name__)

# CORS: local dev dashboard (Streamlit) and other local frontends. Overridable
# via OBLIQ_CORS_ORIGINS (comma-separated). Fase 4 will tighten these when auth
# ships. :3000 = Next.js frontend dev (ARCHITECTURE.md §3 note).
_DEFAULT_CORS = [
    "http://localhost:8501",  # Streamlit dashboard
    "http://127.0.0.1:8501",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",  # Next.js frontend (dev)
    "http://127.0.0.1:3000",  # Next.js frontend (dev)
]
CORS_ORIGINS = [
    o.strip() for o in os.getenv("OBLIQ_CORS_ORIGINS", "").split(",") if o.strip()
] or _DEFAULT_CORS

app = FastAPI(
    title="Obliq API",
    version="0.1.0",
    description=(
        "Analitik pasar obligasi Indonesia (Fase 1): kurva yield pemerintah + "
        "indikator makro. Read-only. Sumber data: DJPPR, BPS, BI."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(watchlist.router)
app.include_router(yield_curve.router)
app.include_router(macro.router)


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler so an internal error is a 500 with a clear message,
    never silently conflated with an 'empty data' 200 response."""
    logger.exception("Internal error handling %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Terjadi kesalahan internal server. Silakan coba lagi nanti."},
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe. Also reports whether the local database responds."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001 -- health endpoint must not crash
        logger.warning("health: DB unreachable: %s", exc)
        db_status = "unreachable"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "obliq-api",
        "database": db_status,
    }