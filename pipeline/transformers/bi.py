"""BI exports (BI7DRR + JISDOR) -> macro_indicators transformer.

WHAT it produces: from validated BI spreadsheet rows, one internal record per
observation:
  - indicator_type 'bi_7drr' -> observation_date = RDG (policy meeting) date,
    value = the 7-day reverse repo rate in percent (e.g. 4.75)
  - indicator_type 'usd_idr' -> observation_date = business day, value = the
    JISDOR reference rate in IDR per USD (e.g. 17913)

Number formats (Sesi 15, validated on real exports -- RULES.md 4 quirks):
  - BI7DRR value arrives as "4.75 %"  (percent sign WITH a leading space)
  - JISDOR value arrives as "17913"   (bare integer Rupiah, no separators)
  - BI7DRR date arrives as "15 Desember 2016"    (Indonesian month name)
  - JISDOR date arrives as "8/7/2026 12:00:00 AM" (US serial, M/D/YYYY)
Both are normalized to a python date (the observation date) and a Decimal.

WHY parse defensively instead of a blind strip: "4.75 %" must be validated as
"<number>" + optional whitespace + "%" before removing -- a value that is not a
percent-shaped string would then be a layout/value drift we surface, not a
silently wrong number (SYSTEM.md 3 / RULES.md 1).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from pipeline.validators.bi import BiSpreadsheet

# "4.75 %", "5,5 %", "6 %" -- percent symbol optional leading whitespace.
_PERCENT_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*%?\s*$")
# JISDOR value: integer Rupiah. "17913". (No comma/period separators observed.)
_RUPIAH_INT_RE = re.compile(r"^\s*(\d{1,12})\s*$")
# JISDOR date: "8/7/2026 12:00:00 AM" -- M/D/YYYY (US serial), time ignored.
_US_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})")

_ID_MONTHS = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
    "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
    "September": 9, "Oktober": 10, "November": 11, "Desember": 12,
}


@dataclass(frozen=True)
class MacroIndicatorRecord:
    """One normalized macro indicator observation, ready for storage."""

    indicator_type: str  # "bi_7drr" | "usd_idr"
    observation_date: date
    value: Decimal
    source: str = "BI"


def _parse_percent(value: str) -> Decimal:
    """'4.75 %' -> Decimal('4.75'). Comma decimal also accepted ('5,5')."""
    match = _PERCENT_RE.match(value)
    if match is None:
        raise ValueError(f"Nilai persen BI tidak valid: {value!r}")
    cleaned = match.group(1).replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Nilai persen BI tidak valid: {value!r}") from exc


def _parse_rupiah_int(value: str) -> Decimal:
    """'17913' -> Decimal('17913')."""
    match = _RUPIAH_INT_RE.match(value)
    if match is None:
        raise ValueError(f"Kurs JISDOR tidak valid (harus integer rupiah): {value!r}")
    try:
        return Decimal(match.group(1))
    except InvalidOperation as exc:
        raise ValueError(f"Kurs JISDOR tidak valid: {value!r}") from exc


def _parse_us_date(value: str) -> date:
    """'8/7/2026 12:00:00 AM' -> date(2026, 8, 7). M/D/YYYY, time ignored."""
    match = _US_DATE_RE.match(value)
    if match is None:
        raise ValueError(f"Tanggal JISDOR tidak valid: {value!r}")
    month, day, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"Tanggal JISDOR di luar rentang kalender: {value!r}") from exc


def _parse_id_date(value: str) -> date:
    """'15 Desember 2016' -> date(2016, 12, 15)."""
    parts = value.split()
    if len(parts) != 3 or not parts[0].isdigit() or not parts[2].isdigit():
        raise ValueError(f"Tanggal BI7DRR tidak valid: {value!r}")
    month = _ID_MONTHS.get(parts[1])
    if month is None:
        raise ValueError(f"Nama bulan tidak dikenal: {parts[1]!r}")
    try:
        return date(int(parts[2]), month, int(parts[0]))
    except ValueError as exc:
        raise ValueError(f"Tanggal BI7DRR di luar rentang kalender: {value!r}") from exc


def _parse_row(spreadsheet: BiSpreadsheet) -> list[MacroIndicatorRecord]:
    records: list[MacroIndicatorRecord] = []
    for row in spreadsheet.rows:
        if spreadsheet.indicator_type == "bi_7drr":
            obs_date = _parse_id_date(row.date_raw)
            value = _parse_percent(row.value_raw)
        elif spreadsheet.indicator_type == "usd_idr":
            obs_date = _parse_us_date(row.date_raw)
            value = _parse_rupiah_int(row.value_raw)
        else:
            raise ValueError(f"indicator_type tidak dikenal: {spreadsheet.indicator_type!r}")
        records.append(
            MacroIndicatorRecord(
                indicator_type=spreadsheet.indicator_type,
                observation_date=obs_date,
                value=value,
            )
        )
    return records


def transform(spreadsheets: list[BiSpreadsheet]) -> list[MacroIndicatorRecord]:
    """Normalize validated BI spreadsheets into storage-ready records."""
    records: list[MacroIndicatorRecord] = []
    for spreadsheet in spreadsheets:
        records.extend(_parse_row(spreadsheet))
    records.sort(key=lambda r: (r.indicator_type, r.observation_date))
    return records