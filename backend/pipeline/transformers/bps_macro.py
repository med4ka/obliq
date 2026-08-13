"""BPS macro indicator transformers -> MacroIndicatorRecord.

Each var has its own granularity:
  - Trade balance (var 498): monthly, 13 pts/year (12 months + annual total)
  - PDB growth (var 104): quarterly, 4 pts/year
  - TPT (var 543): annual, 1 pt/year
  - Foreign reserves (var 1091): annual, 1 pt/year

observation_date is normalized to the LAST DAY of the period (month/quarter/year)
so chart rendering has a consistent anchor point.
"""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MacroIndicatorRecord:
    """One macro indicator observation, ready for storage."""

    indicator_type: str
    observation_date: date
    value: Decimal


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _last_day_of_quarter(year: int, quarter: int) -> date:
    month = quarter * 3
    return _last_day_of_month(year, month)


def _last_day_of_year(year: int) -> date:
    return date(year, 12, 31)


# --- Trade balance (var 498) -> monthly ---

def transform_trade_balance(
    validated: list[tuple[int, int, int, Decimal]],
) -> list[MacroIndicatorRecord]:
    """Transform validated trade balance into monthly observations.

    Input: [(year, th_id, month, value)]
    month=13 or similar is the annual total -- we SKIP it since we only
    want monthly granularity (the annual total can be derived from months).
    """
    results: list[MacroIndicatorRecord] = []
    skipped = 0
    for year, th_id, month, value in validated:
        if month > 12:
            skipped += 1
            continue
        obs_date = _last_day_of_month(year, month)
        results.append(MacroIndicatorRecord(
            indicator_type="trade_balance",
            observation_date=obs_date,
            value=value,
        ))
    if skipped:
        logger.info("Trade balance: skip %d annual total rows", skipped)
    logger.info(
        "Trade balance transform: %d monthly observations (source=BPS)",
        len(results),
    )
    return results


# --- PDB growth (var 104) -> quarterly ---

def transform_pdb_growth(
    validated: list[tuple[int, int, int, Decimal]],
) -> list[MacroIndicatorRecord]:
    """Transform validated PDB growth yoy into quarterly observations.

    Input: [(year, th_id, quarter_code, value)]
    quarter_code encodes which quarter (e.g. 1,2,3,4 or 31,32,33,34).
    We normalize to 1-4.
    """
    results: list[MacroIndicatorRecord] = []
    for year, th_id, quarter_code, value in validated:
        # Normalize quarter: if > 10, last digit is likely the quarter
        if quarter_code > 10:
            quarter = quarter_code % 10
        else:
            quarter = quarter_code
        if quarter < 1 or quarter > 4:
            logger.warning("PDB growth: quarter di luar 1-4 (%d), skip", quarter_code)
            continue
        obs_date = _last_day_of_quarter(year, quarter)
        results.append(MacroIndicatorRecord(
            indicator_type="pdb_yoy",
            observation_date=obs_date,
            value=value,
        ))
    results.sort(key=lambda r: r.observation_date)
    logger.info(
        "PDB growth transform: %d quarterly observations (source=BPS)",
        len(results),
    )
    return results


# --- TPT (var 543) -> annual ---

def transform_tpt(
    validated: list[tuple[int, int, Decimal]],
) -> list[MacroIndicatorRecord]:
    """Transform validated TPT into annual observations.

    Input: [(year, th_id, value)]
    BPS publishes TPT twice a year (Feb & Aug) -> 2 values per year.
    We average them for the annual figure. Sorting by th_id ensures
    earlier semester is processed first (idempotent).
    """
    validated.sort(key=lambda x: (x[0], x[1]))
    by_year: dict[int, list[Decimal]] = {}
    for year, th_id, value in validated:
        by_year.setdefault(year, []).append(value)
    results: list[MacroIndicatorRecord] = []
    for year, values in sorted(by_year.items()):
        avg = sum(values, Decimal("0")) / Decimal(str(len(values)))
        obs_date = _last_day_of_year(year)
        results.append(MacroIndicatorRecord(
            indicator_type="tpt",
            observation_date=obs_date,
            value=avg,
        ))
    results.sort(key=lambda r: r.observation_date)
    logger.info(
        "TPT transform: %d annual observations (averaged from %d raw, source=BPS)",
        len(results), len(validated),
    )
    return results


# --- Foreign reserves (var 1091) -> annual ---

def transform_foreign_reserves(
    validated: list[tuple[int, int, Decimal]],
) -> list[MacroIndicatorRecord]:
    """Transform validated foreign reserves into annual observations.

    Input: [(year, th_id, value)]
    """
    results: list[MacroIndicatorRecord] = []
    for year, th_id, value in validated:
        obs_date = _last_day_of_year(year)
        results.append(MacroIndicatorRecord(
            indicator_type="foreign_reserves",
            observation_date=obs_date,
            value=value,
        ))
    results.sort(key=lambda r: r.observation_date)
    logger.info(
        "Foreign reserves transform: %d annual observations (source=BPS)",
        len(results),
    )
    return results
