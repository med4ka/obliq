"""BPS IHK -> inflation YoY transformer.

WHAT it computes: Indonesian yearly (YoY) inflation from monthly IHK index
values fetched from BPS.

WHY compute it ourselves instead of taking an official "YoY" figure: BPS does
not expose a ready-made YoY series on this API var. It publishes MtM (bulanan,
var_id=1) and the raw index level. Inflation YoY has a stable definition
independent of publication quirks:

    YoY(t) = (IHK(t) - IHK(t-12 months)) / IHK(t-12 months) * 100

where IHK(t) is the national consumer price index for month t (basis 2018=100).
We compute it from the index level so the dashboard shows a figure that is
exactly reproducible from source data (SYSTEM.md 1.2: every number traceable).

Gap handling: the first 12 months of any fetched range have no 12-months-earlier
pair (e.g. Jan 2020 for a range starting 2020 -> needs Jan 2019, not fetched).
Such points are skipped -- but NOT silently: this module logs each skip so the
operator can see exactly which observation dates were omitted and why
(SYSTEM.md 3: no silent failures).
"""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pipeline.validators.bps import BpsMonthObservation, BpsYearData

logger = logging.getLogger(__name__)

# Decimal, never float, for all financial values (SYSTEM.md 1.5).
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class InflationYoY:
    """One computed YoY inflation observation, ready for storage."""

    observation_date: date  # last day of the observed calendar month
    value: Decimal  # percent, e.g. Decimal("2.33") for 2.33%


def _index_by_month(data: list[BpsYearData]) -> dict[int, dict[int, Decimal]]:
    """Group validated observations as {year: {month: IHK}}."""
    by_year: dict[int, dict[int, Decimal]] = {}
    for year_data in data:
        bucket: dict[int, Decimal] = {}
        for obs in year_data.observations:
            bucket[obs.month] = obs.value
        by_year[year_data.year] = bucket
    return by_year


def transform(data: list[BpsYearData]) -> list[InflationYoY]:
    """Compute YoY inflation for every (year, month) that has a 12-month-back pair.

    Points without a pair are logged and skipped (never interpolated). Raising
    requires the data to have come from validate_years (already enforced by the
    Pydantic types above).
    """
    by_year = _index_by_month(data)
    results: list[InflationYoY] = []
    skipped: list[tuple[int, int, str]] = []

    for year in sorted(by_year):
        for month in sorted(by_year[year]):
            previous_year = year - 1
            prev_value = by_year.get(previous_year, {}).get(month)
            current_value = by_year[year][month]
            if prev_value is None:
                skipped.append(
                    (year, month, f"tidak ada IHK {previous_year}-{month:02d}")
                )
                continue
            # May imply no change only if equal; avoid division by zero silently.
            if prev_value == 0:
                skipped.append(
                    (year, month, f"IHK {previous_year}-{month:02d} = 0 (tak dapat dibagi)")
                )
                continue
            yoy = ((current_value - prev_value) / prev_value) * HUNDRED
            results.append(
                InflationYoY(
                    observation_date=_last_day_of_month(year, month),
                    value=yoy,
                )
            )

    for year, month, reason in skipped:
        logger.warning(
            "Skip inflasi YoY %d-%02d: %s (tidak dihitung, tanpa interpolasi)",
            year, month, reason,
        )
    return results


def _last_day_of_month(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)