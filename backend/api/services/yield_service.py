"""Yield curve read logic (api layer, read-only).

Serves the "current" government yield curve -- the latest known yield per
active bond (auction results are the data source, so "latest observation per
bond" is the closest truthful sense of "current", SYSTEM.md 1.1 -- we never
invent a fresher point) -- and the yield history of a single bond.

Numbers leave as Decimal (SCHEMA.md / SYSTEM.md 1.5); the response schemas
serialize them to exact strings.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api import schemas
from db.models import Bond, YieldObservation


def build_current_curve(session: Session) -> schemas.YieldCurveCurrentResponse:
    """Latest yield per active bond, ordered by tenor (a usable curve)."""
    # Subquery: max observation_date per bond (idempotency key is per
    # bond+date, so a bond has exactly one row per date -- max is unambiguous).
    latest = (
        select(
            YieldObservation.bond_id,
            func.max(YieldObservation.observation_date).label("latest_date"),
        )
        .group_by(YieldObservation.bond_id)
        .subquery()
    )

    rows = session.execute(
        select(Bond, YieldObservation)
        .join(latest, latest.c.bond_id == Bond.id)
        .join(
            YieldObservation,
            (YieldObservation.bond_id == latest.c.bond_id)
            & (YieldObservation.observation_date == latest.c.latest_date),
        )
        .where(Bond.is_active.is_(True))
        .order_by(Bond.tenor_years.asc().nullslast(), Bond.code.asc())
    ).all()

    items = [
        schemas.YieldCurvePoint(
            bond_code=bond.code,
            bond_name=bond.name,
            tenor_years=bond.tenor_years,
            coupon_rate=bond.coupon_rate,
            maturity_date=bond.maturity_date,
            observation_date=obs.observation_date,
            yield_value=obs.yield_value,
            price=obs.price,
            source=obs.source,
            fetched_at=obs.fetched_at,
            is_estimated=obs.is_estimated,
        )
        for bond, obs in rows
    ]

    if not items:
        return schemas.YieldCurveCurrentResponse(
            status="empty",
            message="Belum ada observasi yield untuk obligasi aktif di database.",
        )

    return schemas.YieldCurveCurrentResponse(
        status="ok",
        as_of=max(item.observation_date for item in items),
        count=len(items),
        items=items,
    )


def build_bond_history(
    session: Session,
    bond_code: str,
    start: date | None = None,
    end: date | None = None,
) -> schemas.YieldHistoryResponse:
    """Yield observations of one bond, optionally bounded by [start, end]."""
    bond = session.scalars(select(Bond).where(Bond.code == bond_code)).first()
    if bond is None:
        return schemas.YieldHistoryResponse(
            status="not_found",
            message=f"Bond '{bond_code}' tidak ditemukan di database.",
            bond_code=bond_code,
        )

    stmt = (
        select(YieldObservation)
        .where(YieldObservation.bond_id == bond.id)
        .order_by(YieldObservation.observation_date.asc())
    )
    if start is not None:
        stmt = stmt.where(YieldObservation.observation_date >= start)
    if end is not None:
        stmt = stmt.where(YieldObservation.observation_date <= end)

    obs_list = session.scalars(stmt).all()

    items = [
        schemas.YieldHistoryItem(
            observation_date=obs.observation_date,
            yield_value=obs.yield_value,
            price=obs.price,
            source=obs.source,
            fetched_at=obs.fetched_at,
            is_estimated=obs.is_estimated,
        )
        for obs in obs_list
    ]

    if not items:
        range_hint = f" pada rentang {start} s.d. {end}" if start or end else ""
        return schemas.YieldHistoryResponse(
            status="empty",
            message=f"Tidak ada observasi yield untuk {bond_code}{range_hint}.",
            bond_code=bond_code,
            bond_name=bond.name,
            start=start,
            end=end,
        )

    return schemas.YieldHistoryResponse(
        status="ok",
        bond_code=bond_code,
        bond_name=bond.name,
        start=start,
        end=end,
        count=len(items),
        items=items,
    )