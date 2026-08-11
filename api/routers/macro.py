"""Router: /api/macro (read-only macro indicator endpoints)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import get_db
from api.services import macro_service

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/latest", response_model=schemas.MacroLatestResponse)
def read_macro_latest(db: Session = Depends(get_db)) -> schemas.MacroLatestResponse:
    """Snapshot: most recent observation of every macro indicator type."""
    return macro_service.build_macro_latest(db)


@router.get("/{indicator_type}", response_model=schemas.MacroHistoryResponse)
def read_macro_history(
    indicator_type: str,
    start: date | None = Query(default=None, description="inclusive"),
    end: date | None = Query(default=None, description="inclusive"),
    db: Session = Depends(get_db),
) -> schemas.MacroHistoryResponse:
    """History of one indicator (e.g. inflation_yoy), optionally ranged."""
    if start is not None and end is not None and start > end:
        raise HTTPException(
            status_code=422,
            detail=f"Rentang tidak valid: start ({start}) setelah end ({end}).",
        )
    return macro_service.build_macro_history(db, indicator_type, start, end)