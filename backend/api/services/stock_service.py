"""IHSG / LQ45 stock read logic (api layer, read-only).

Follows same pattern as macro_service.py: build_stock_history for ranged
observations, build_stock_latest for the most recent close, build_stock_list
for the full LQ45 listing with latest prices.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api import schemas
from db.models import Stock, StockObservation


def _resolve_stock(
    session: Session, stock_code: str
) -> Stock | None:
    return session.scalar(select(Stock).where(Stock.code == stock_code))


def build_stock_history(
    session: Session,
    stock_code: str = "^JKSE",
    start: date | None = None,
    end: date | None = None,
) -> schemas.StockHistoryResponse:
    """Daily observations for one stock, optionally bounded by [start, end]."""
    stock = _resolve_stock(session, stock_code)
    if stock is None:
        return schemas.StockHistoryResponse(
            status="empty",
            message=f"Stock '{stock_code}' tidak ditemukan.",
            stock_code=stock_code,
        )

    stmt = (
        select(StockObservation)
        .where(StockObservation.stock_id == stock.id)
        .order_by(StockObservation.observation_date.asc())
    )
    if start is not None:
        stmt = stmt.where(StockObservation.observation_date >= start)
    if end is not None:
        stmt = stmt.where(StockObservation.observation_date <= end)

    rows = session.scalars(stmt).all()
    items = [
        schemas.StockObservationItem(
            observation_date=r.observation_date,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            adj_close=r.adj_close,
            volume=r.volume,
            source=r.source,
            fetched_at=r.fetched_at,
        )
        for r in rows
    ]

    label = stock.name or stock_code
    if not items:
        range_hint = f" pada rentang {start} s.d. {end}" if start or end else ""
        return schemas.StockHistoryResponse(
            status="empty",
            message=f"Tidak ada data {label}{range_hint}.",
            stock_code=stock_code,
            start=start,
            end=end,
        )

    return schemas.StockHistoryResponse(
        status="ok",
        stock_code=stock_code,
        start=start,
        end=end,
        count=len(items),
        items=items,
    )


def build_stock_latest(
    session: Session,
    stock_code: str = "^JKSE",
) -> schemas.StockLatestResponse:
    stock = _resolve_stock(session, stock_code)
    if stock is None:
        return schemas.StockLatestResponse(
            status="empty",
            message=f"Stock '{stock_code}' tidak ditemukan.",
            stock_code=stock_code,
        )

    max_date = session.scalar(
        select(func.max(StockObservation.observation_date))
        .where(StockObservation.stock_id == stock.id)
    )
    if max_date is None:
        label = stock.name or stock_code
        return schemas.StockLatestResponse(
            status="empty",
            message=f"Belum ada data {label}.",
            stock_code=stock_code,
        )

    row = session.scalar(
        select(StockObservation)
        .where(
            StockObservation.stock_id == stock.id,
            StockObservation.observation_date == max_date,
        )
    )
    return schemas.StockLatestResponse(
        status="ok",
        stock_code=stock_code,
        observation_date=row.observation_date,
        close=row.close,
        adj_close=row.adj_close,
        source=row.source,
        fetched_at=row.fetched_at,
    )


def build_stock_list(session: Session) -> schemas.StockListResponse:
    """All equity stocks with their latest close and day change."""
    stocks = session.scalars(
        select(Stock).where(Stock.kind == "equity").order_by(Stock.code.asc())
    ).all()
    if not stocks:
        return schemas.StockListResponse(
            status="empty", message="Belum ada data saham."
        )

    items: list[schemas.StockListItem] = []
    for s in stocks:
        latest = session.scalar(
            select(StockObservation)
            .where(StockObservation.stock_id == s.id)
            .order_by(StockObservation.observation_date.desc())
            .limit(1)
        )
        prev = None
        if latest:
            prev = session.scalar(
                select(StockObservation)
                .where(
                    StockObservation.stock_id == s.id,
                    StockObservation.observation_date
                    < latest.observation_date,
                )
                .order_by(StockObservation.observation_date.desc())
                .limit(1)
            )

        close = latest.close if latest else None
        prev_close = prev.close if prev else None
        change = None
        change_pct = None
        if close is not None and prev_close is not None and prev_close != 0:
            change = close - prev_close
            change_pct = (change / prev_close) * 100

        items.append(
            schemas.StockListItem(
                code=s.code,
                name=s.name,
                sector=s.sector,
                kind=s.kind,
                latest_close=close,
                latest_date=latest.observation_date if latest else None,
                change=change,
                change_pct=change_pct,
            )
        )

    return schemas.StockListResponse(status="ok", count=len(items), items=items)
