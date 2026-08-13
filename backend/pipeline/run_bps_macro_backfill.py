"""Backfill 4 new BPS macro indicators: trade_balance, pdb_yoy, tpt, foreign_reserves.
Run checkpoint per indicator. Usage: python -m pipeline.run_bps_macro_backfill [indicator_name]
Omit indicator_name to show menu.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime

from db.connection import get_engine
from pipeline.fetchers.bps import fetch_trade_balance, fetch_pdb_growth, fetch_tpt, fetch_foreign_reserves
from pipeline.validators.bps_macro import validate_trade_balance, validate_pdb_growth, validate_tpt, validate_foreign_reserves
from pipeline.transformers.bps_macro import transform_trade_balance, transform_pdb_growth, transform_tpt, transform_foreign_reserves
from pipeline.storage.bps import store_macro

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

INDICATORS = {
    "trade_balance": {
        "desc": "Neraca Perdagangan 2017-2026",
        "fetch": fetch_trade_balance,
        "validate": validate_trade_balance,
        "transform": transform_trade_balance,
    },
    "pdb_yoy": {
        "desc": "PDB Growth 2011-2026",
        "fetch": fetch_pdb_growth,
        "validate": validate_pdb_growth,
        "transform": transform_pdb_growth,
    },
    "tpt": {
        "desc": "TPT ~2009-2026",
        "fetch": fetch_tpt,
        "validate": validate_tpt,
        "transform": transform_tpt,
    },
    "foreign_reserves": {
        "desc": "Cadangan Devisa 2016-2025",
        "fetch": fetch_foreign_reserves,
        "validate": validate_foreign_reserves,
        "transform": transform_foreign_reserves,
    },
}


def _filter_available(raw: list) -> list:
    available = [r for r in raw if r.body.get("data-availability") == "available"]
    skipped = len(raw) - len(available)
    if skipped:
        skipped_years = [r.year for r in raw if r.body.get("data-availability") != "available"]
        logger.info("  Skip %d unavailable years: %s", skipped, skipped_years)
    return available


def run_one(name: str) -> dict:
    info = INDICATORS[name]
    engine = get_engine()
    now = datetime.now()

    logger.info("=== %s (%s) ===", name, info["desc"])
    logger.info("Fetching...")
    raw = info["fetch"]()
    logger.info("  Got %d year responses", len(raw))

    raw = _filter_available(raw)

    logger.info("Validating...")
    validated = info["validate"](raw)
    logger.info("  Validated %d raw data points", len(validated))

    logger.info("Transforming...")
    records = info["transform"](validated)
    logger.info("  Transformed %d records", len(records))

    logger.info("Storing (upsert)...")
    counts = store_macro(engine, records, fetched_at=now)
    total = sum(counts.values())
    logger.info("  Stored %d total rows", total)

    return {
        "indicator": name,
        "raw_years": len(raw),
        "validated_points": len(validated),
        "records": len(records),
        "stored": total,
        "ranges": _get_ranges(engine, name),
    }


def _get_ranges(engine, indicator_type: str) -> str:
    from sqlalchemy import text
    with engine.connect() as c:
        row = c.execute(
            text("SELECT min(observation_date), max(observation_date), count(*) FROM macro_indicators WHERE indicator_type=:t"),
            {"t": indicator_type},
        ).one()
        if row[2] == 0:
            return "(no data)"
        return f"{row[0]} .. {row[1]} ({row[2]} obs)"


def main():
    args = sys.argv[1:]
    targets = [a for a in args if a in INDICATORS]

    if not targets:
        print("Available indicators:")
        for k, v in INDICATORS.items():
            print(f"  {k:20s} - {v['desc']}")
        print(f"\nUsage: python -m pipeline.run_bps_macro_backfill <indicator1> [indicator2 ...]")
        return

    for name in targets:
        result = run_one(name)
        print(f"\n=== CHECKPOINT: {name} ===")
        print(f"  Raw years fetched: {result['raw_years']}")
        print(f"  Validated points:  {result['validated_points']}")
        print(f"  Transformed:       {result['records']}")
        print(f"  Stored (upsert):   {result['stored']}")
        print(f"  Range:             {result['ranges']}")
        print("")

    print("=== ALL DONE ===")


if __name__ == "__main__":
    main()
