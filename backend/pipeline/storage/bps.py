"""Storage of BPS indicators into PostgreSQL.

Upsert contract (ARCHITECTURE.md 4): re-running a fetch for the same
(observation_date) must update the existing row, never insert a duplicate.
Relies on the unique constraint uq_macro_type_date over
(indicator_type, observation_date) defined in SCHEMA.md and enforced in the
formal migration.

Originally for inflation YoY (inflation_yoy), now extended with 4 new macro
indicators (Sesi 44): trade_balance, pdb_yoy, tpt, foreign_reserves.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.transformers.bps import InflationYoY
from pipeline.transformers.bps_macro import MacroIndicatorRecord

logger = logging.getLogger(__name__)

INDICATOR_TYPE_YOY = "inflation_yoy"
SOURCE_BPS = "BPS"

UPSERT_SQL = text(
    """
    INSERT INTO macro_indicators (indicator_type, observation_date, value, source, fetched_at)
    VALUES (:indicator_type, :observation_date, :value, :source, :fetched_at)
    ON CONFLICT (indicator_type, observation_date)
    DO UPDATE SET value = EXCLUDED.value,
                  source = EXCLUDED.source,
                  fetched_at = EXCLUDED.fetched_at
    """
)


def store(engine: Engine, observations: list[InflationYoY], fetched_at: datetime | None = None) -> int:
    """Upsert computed YoY observations. Returns number of rows written/updated.

    Idempotent: same (indicator_type, observation_date) as a previous run just
    updates value + source + fetched_at in place.
    """
    return _store_records(
        engine,
        [(INDICATOR_TYPE_YOY, obs.observation_date, obs.value) for obs in observations],
        fetched_at,
        label=INDICATOR_TYPE_YOY,
    )


def store_macro(
    engine: Engine,
    records: list[MacroIndicatorRecord],
    fetched_at: datetime | None = None,
) -> dict[str, int]:
    """Upsert macro indicator records (any type). Returns {indicator_type: count}.

    Handles multiple indicator_types in one call.
    """
    fetched_at = fetched_at or datetime.now()
    counts: dict[str, int] = {}
    with engine.begin() as conn:
        for record in records:
            conn.execute(
                UPSERT_SQL,
                {
                    "indicator_type": record.indicator_type,
                    "observation_date": record.observation_date,
                    "value": record.value,
                    "source": SOURCE_BPS,
                    "fetched_at": fetched_at,
                },
            )
            counts[record.indicator_type] = counts.get(record.indicator_type, 0) + 1
    for itype, cnt in sorted(counts.items()):
        logger.info("BPS upsert selesai: %d observasi (indicator=%s source=%s)", cnt, itype, SOURCE_BPS)
    return counts


def _store_records(
    engine: Engine,
    records: list[tuple[str, datetime.date, Decimal]],
    fetched_at: datetime | None = None,
    label: str = "",
) -> int:
    fetched_at = fetched_at or datetime.now()
    count = 0
    with engine.begin() as conn:
        for indicator_type, observation_date, value in records:
            conn.execute(
                UPSERT_SQL,
                {
                    "indicator_type": indicator_type,
                    "observation_date": observation_date,
                    "value": value,
                    "source": SOURCE_BPS,
                    "fetched_at": fetched_at,
                },
            )
            count += 1
    logger.info("BPS upsert selesai: %d observasi (indicator=%s source=%s)", count, label or "?", SOURCE_BPS)
    return count