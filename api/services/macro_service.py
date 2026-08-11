"""Macro indicator read logic (api layer, read-only).

Indicators live in `macro_indicators` (inflation_yoy, bi_7drr, usd_idr).
Every macro item is honesty-tagged in the API layer (RULES.md 3): rows whose
source starts with "DUMMY" (or is empty/unknown) come with `is_dummy=True` and
the exact badge text in `notice`, so consumers never present them as official
statistics. This signal is preserved end-to-end, never stripped at the API.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api import schemas
from db.models import MacroIndicator


def _is_dummy(source: str | None) -> bool:
    """RULES.md 3: empty/unknown source or "DUMMY*" prefix = not official data."""
    if source is None or source.strip() == "":
        return True
    return source.startswith("DUMMY")


def _notice(source: str | None) -> str | None:
    """Return the badge text only for non-official rows, else None."""
    return schemas.DUMMY_BADGE if _is_dummy(source) else None


def _to_item(row: MacroIndicator) -> schemas.MacroItem:
    return schemas.MacroItem(
        indicator_type=row.indicator_type,
        observation_date=row.observation_date,
        value=row.value,
        source=row.source,
        fetched_at=row.fetched_at,
        is_dummy=_is_dummy(row.source),
        notice=_notice(row.source),
    )


def build_macro_history(
    session: Session,
    indicator_type: str,
    start: date | None = None,
    end: date | None = None,
) -> schemas.MacroHistoryResponse:
    """Observations of one indicator, optionally bounded by [start, end]."""
    stmt = (
        select(MacroIndicator)
        .where(MacroIndicator.indicator_type == indicator_type)
        .order_by(MacroIndicator.observation_date.asc())
    )
    if start is not None:
        stmt = stmt.where(MacroIndicator.observation_date >= start)
    if end is not None:
        stmt = stmt.where(MacroIndicator.observation_date <= end)

    rows = session.scalars(stmt).all()
    items = [_to_item(r) for r in rows]

    if not items:
        range_hint = f" pada rentang {start} s.d. {end}" if start or end else ""
        return schemas.MacroHistoryResponse(
            status="empty",
            message=f"Tidak ada data indikator '{indicator_type}'{range_hint}.",
            indicator_type=indicator_type,
            start=start,
            end=end,
        )

    return schemas.MacroHistoryResponse(
        status="ok",
        indicator_type=indicator_type,
        start=start,
        end=end,
        count=len(items),
        items=items,
    )


def build_macro_latest(session: Session) -> schemas.MacroLatestResponse:
    """Snapshot: the most recent observation of every known indicator type."""
    latest = (
        select(
            MacroIndicator.indicator_type,
            func.max(MacroIndicator.observation_date).label("latest_date"),
        )
        .group_by(MacroIndicator.indicator_type)
        .subquery()
    )

    rows = session.execute(
        select(MacroIndicator)
        .join(
            latest,
            (latest.c.indicator_type == MacroIndicator.indicator_type)
            & (latest.c.latest_date == MacroIndicator.observation_date),
        )
        .order_by(MacroIndicator.indicator_type.asc())
    ).scalars().all()

    items = [_to_item(r) for r in rows]

    if not items:
        return schemas.MacroLatestResponse(
            status="empty",
            message="Belum ada indikator makro di database.",
        )

    return schemas.MacroLatestResponse(status="ok", count=len(items), items=items)