"""Seed DUMMY example macro indicators into the local PostgreSQL database.

IMPORTANT: These rows carry source='DUMMY_CONTOH'. They are NOT official
statistics (SYSTEM.md 1.1). Their only purpose is to let the dashboard be
built and rendered before real fetchers exist. Every consumer (dashboard/API)
MUST render a prominent badge when source starts with 'DUMMY'.

This script is idempotent: re-running it replaces only DUMMY rows, never
touches rows from real sources.

Run from repo root (needs .env with DATABASE_URL):
    python -m db.seed_dummy_data
"""
from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DUMMY_SOURCE = "DUMMY_CONTOH"

# Interim bootstrap DDL so the seed can run before Fase 1 models/migrations exist.
# indicator_type is VARCHAR here; Fase 1 Alembic formalizes it (SCHEMA.md uses an enum).
BOOTSTRAP_DDL = """
CREATE TABLE IF NOT EXISTS macro_indicators (
    id SERIAL PRIMARY KEY,
    indicator_type VARCHAR(50) NOT NULL,
    observation_date DATE NOT NULL,
    value NUMERIC(12,4) NOT NULL,
    source VARCHAR(100) NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_macro_type_date UNIQUE (indicator_type, observation_date)
);
"""

# 6 monthly rows of Indonesian inflation (YoY %). Plausible magnitudes, but
# explicitly dummy -- never to be presented as official BPS figures.
DUMMY_INFLATION_YOY: list[tuple[date, Decimal]] = [
    (date(2026, 1, 31), Decimal("2.28")),
    (date(2026, 2, 28), Decimal("2.35")),
    (date(2026, 3, 31), Decimal("2.51")),
    (date(2026, 4, 30), Decimal("2.44")),
    (date(2026, 5, 31), Decimal("2.20")),
    (date(2026, 6, 30), Decimal("2.10")),
]

INSERT_SQL = """
INSERT INTO macro_indicators (indicator_type, observation_date, value, source, fetched_at)
VALUES (:indicator_type, :observation_date, :value, :source, :fetched_at)
"""

DELETE_DUMMY_SQL = "DELETE FROM macro_indicators WHERE source LIKE 'DUMMY%'"


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL kosong. Salin .env.example ke .env terlebih dahulu.")

    engine = create_engine(database_url)
    fetched_at = datetime.now()

    with engine.begin() as conn:
        conn.execute(text(BOOTSTRAP_DDL))
        deleted = conn.execute(text(DELETE_DUMMY_SQL)).rowcount
        for obs_date, value in DUMMY_INFLATION_YOY:
            conn.execute(
                text(INSERT_SQL),
                {
                    "indicator_type": "inflation_yoy",
                    "observation_date": obs_date,
                    "value": value,
                    "source": DUMMY_SOURCE,
                    "fetched_at": fetched_at,
                },
            )

        count = conn.execute(
            text("SELECT count(*) FROM macro_indicators WHERE source LIKE 'DUMMY%'")
        ).scalar()

    print(f"Seeded {len(DUMMY_INFLATION_YOY)} rows, source='{DUMMY_SOURCE}'."
          f" (old dummy rows removed: {deleted}, total dummy rows now: {count})")


if __name__ == "__main__":
    main()