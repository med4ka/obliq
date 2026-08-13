"""Storage of BI macro indicators (BI7DRR, JISDOR USD/IDR) into PostgreSQL.

Upsert contract (ARCHITECTURE.md 4): re-running a fetch for the same
(indicator_type, observation_date) must update the existing row, never insert a
duplicate. Relies on the unique constraint uq_macro_type_date over
(indicator_type, observation_date) defined in SCHEMA.md / db/models.py.
`source='BI'` and `fetched_at` are audit fields (SCHEMA.md): every rendered
number must be traceable to where it came from and when.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pipeline.transformers.bi import MacroIndicatorRecord

logger = logging.getLogger(__name__)

# indicator_type values (SCHEMA.md macro_indicators.indicator_type).
INDICATOR_BI7DRR = "bi_7drr"
INDICATOR_USD_IDR = "usd_idr"
SOURCE_BI = "BI"

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


def store(
    engine: Engine,
    records: list[MacroIndicatorRecord],
    fetched_at: datetime | None = None,
) -> dict[str, int]:
    """Upsert BI records into macro_indicators. Returns {indicator_type: count}.

    Idempotent: same (indicator_type, observation_date) as a previous run just
    updates value + source + fetched_at in place (ARCHITECTURE.md 4).
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
                    "value": record.value,  # Decimal stays Decimal through the driver
                    "source": SOURCE_BI,
                    "fetched_at": fetched_at,
                },
            )
            counts[record.indicator_type] = counts.get(record.indicator_type, 0) + 1
    logger.info(
        "BI upsert selesai: %s (source=%s)", counts, SOURCE_BI,
    )
    return counts