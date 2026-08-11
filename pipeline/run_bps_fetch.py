"""Manual end-to-end BPS fetch: fetch -> validate -> transform -> store.

Fase 1 is intentionally at "make one source fully work" stage, so this runs
manually (no APScheduler yet; scheduling comes later per PROGRESS.md).

Run from repo root:
    python -m pipeline.run_bps_fetch

Prints a short summary of how many YoY rows were written and which month-pairs
were skipped (gap, not interpolated -- SYSTEM.md 3).
"""
from __future__ import annotations

import logging
from datetime import datetime

from db.connection import get_engine
from pipeline.fetchers.bps import fetch
from pipeline.storage.bps import store
from pipeline.transformers.bps import transform
from pipeline.validators.bps import validate_years

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    engine = get_engine()

    logger.info("Fetching BPS IHK...")
    raw = fetch()

    logger.info("Validating %d year responses...", len(raw))
    validated = validate_years(raw)

    logger.info("Computing YoY inflation...")
    yoy = transform(validated)

    logger.info("Upserting %d rows into macro_indicators (source=BPS)...", len(yoy))
    written = store(engine, yoy, fetched_at=datetime.now())

    print(
        f"Selesai: {len(raw)} tahun di-fetch, {len(validated)} valid, "
        f"{len(yoy)} YoY dihitung, {written} di-upsert (source='BPS')."
    )


if __name__ == "__main__":
    main()