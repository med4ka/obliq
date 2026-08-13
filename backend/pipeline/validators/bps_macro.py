"""Pydantic validation of BPS macro indicator responses (var 498, 104, 543, 1091).

Each BPS var returns `datacontent` as a dict of `{key: value}` where the key
structure differs per var. This module provides one validate function per var.

Raises ValueError (via Pydantic ValidationError) on malformed data -- never let
malformed data reach the transformer (ARCHITECTURE.md 4).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator

from pipeline.fetchers.bps import BpsVarResponse


class BpsMacroRawResponse(BaseModel):
    """Top-level shape of one BPS API response for macro indicators."""

    status: str
    data_availability: str = Field(alias="data-availability")
    last_update: str | None = None
    var: list[dict] = Field(default_factory=list)
    vervar: list[dict] = Field(default_factory=list)
    tahun: list[dict] = Field(default_factory=list)
    datacontent: dict[str, str | float | int] = Field(default_factory=dict)
    related: Any = None

    model_config = {"populate_by_name": True}

    @field_validator("status")
    @classmethod
    def _status_must_be_ok(cls, v: str) -> str:
        if v != "OK":
            raise ValueError(f"status BPS = {v!r}, harus 'OK'")
        return v


def _extract_year(payload: BpsMacroRawResponse) -> int | None:
    if not payload.tahun or "label" not in payload.tahun[0]:
        return None
    try:
        return int(payload.tahun[0]["label"])
    except (TypeError, ValueError):
        return None


def _extract_th_id(payload: BpsMacroRawResponse) -> int | None:
    if not payload.tahun or "val" not in payload.tahun[0]:
        return None
    try:
        return int(payload.tahun[0]["val"])
    except (TypeError, ValueError):
        return None


def _parse_datacontent_values(
    dc: dict[str, str | float | int],
) -> dict[str, Decimal]:
    """Convert all datacontent values to Decimal, raising on non-numeric."""
    result: dict[str, Decimal] = {}
    for key, raw_value in dc.items():
        try:
            result[key] = Decimal(str(raw_value))
        except InvalidOperation as exc:
            raise ValueError(
                f"Nilai non-numerik di datacontent, key={key!r} value={raw_value!r}"
            ) from exc
    return result


# --- Trade balance (var 498) ---
# Key format: vervar(4) + var(3) + th_id(04d) + month(1-2)
# E.g. "999949801244" -> vervar=9999, var=498, th=0124, month=4
# 13 pts/year: months 1-12 + annual (month=13 or similar)

_KEY_RE_498 = re.compile(r"^\d{7}\d{4}\d{1,2}$")


def validate_trade_balance(responses: list[BpsVarResponse]) -> list[tuple[int, int, int, Decimal]]:
    """Validate trade balance responses. Returns [(year, th_id, month, value)]."""
    result: list[tuple[int, int, int, Decimal]] = []
    for raw in responses:
        body = raw.body
        payload = BpsMacroRawResponse.model_validate(body)
        if payload.data_availability != "available":
            raise ValueError(
                f"BPS trade balance 'data-availability' = {payload.data_availability!r}"
            )
        year = _extract_year(payload)
        th_id = _extract_th_id(payload)
        if year is None or th_id is None:
            raise ValueError("Respons BPS tidak punya tahun[0] yang valid")
        dc = _parse_datacontent_values(payload.datacontent)
        for key, value in dc.items():
            if not _KEY_RE_498.match(key):
                raise ValueError(f"Key datacontent trade balance tidak dikenali: {key!r}")
            # key = 9999(vervar) + 498(var) + th_id_4d + month
            th_str = f"{th_id:04d}"
            idx = key.rfind(th_str)
            if idx < 0:
                raise ValueError(f"Key {key!r} tidak mengandung th_id {th_id}")
            month_str = key[idx + len(th_str):]
            month = int(month_str)
            result.append((year, th_id, month, value))
    return result


# --- PDB growth (var 104, turvar=5) ---
# Key format: vervar(5) + turvar(1) + var(3) + th_id(04d) + quarter(1)
# E.g. "99003104512631" -> vervar=99003, turvar=1?, var=104, th=0126, quarter=31?
# Actually: from research, "13050104512631" = vervar=13050 + ? + 104 + 0126 + 31
# The vervar list includes values like 99001, 99002, 99003 (PDB total = 99003)
# We only fetch with vervar=99003 (PDB total), so key starts with "99003"
# Key structure: vervar(5) + ??? + var(3) + th_id(04d) + suffix
# Looking at "99003104512631": 5+2+3+4+? = 14 chars... 
# Actually: the response has turvar field showing turvar_id values 3,4,5
# So the key includes turvar value somehow
# Key format (from live inspection of var 104 data):
# {vervar:5}{prefix:1}{pad:2}{turvar:1}{th_id:3-4}{quarter:2}
# th_id may be padded (4 chars) or unpadded (3 chars) depending on year.
# E.g. "11000104512631" = vervar=11000 + prefix=1 + pad=04 + turvar=5 + th=126 + q=31

_KEY_RE_104 = re.compile(r"^\d{12,14}$")


def validate_pdb_growth(responses: list[BpsVarResponse]) -> list[tuple[int, int, int, Decimal]]:
    """Validate PDB growth responses. Returns [(year, th_id, quarter, value)]."""
    result: list[tuple[int, int, int, Decimal]] = []
    for raw in responses:
        body = raw.body
        payload = BpsMacroRawResponse.model_validate(body)
        if payload.data_availability != "available":
            raise ValueError(
                f"BPS PDB growth 'data-availability' = {payload.data_availability!r}"
            )
        year = _extract_year(payload)
        th_id = _extract_th_id(payload)
        if year is None or th_id is None:
            raise ValueError("Respons BPS tidak punya tahun[0] yang valid")
        dc = _parse_datacontent_values(payload.datacontent)
        # Try padded then unpadded th_id
        th_candidates = [f"{th_id:04d}", f"{th_id:03d}", str(th_id)]
        seen_quarters: set[int] = set()
        for key, value in dc.items():
            found = False
            for th_str in th_candidates:
                idx = key.rfind(th_str)
                if idx >= 0:
                    period_str = key[idx + len(th_str):]
                    if period_str and period_str.isdigit():
                        quarter = int(period_str)
                        if 1 <= quarter <= 99:
                            seen_quarters.add(quarter)
                            result.append((year, th_id, quarter, value))
                            found = True
                            break
            if not found:
                raise ValueError(f"Key PDB {key!r} tidak mengandung th_id {th_id}")
        if not seen_quarters:
            raise ValueError(f"Tidak ada data PDB untuk th_id {th_id}")
    return result


# --- TPT (var 543, vervar=9999) ---
# Key format: vervar(4) + var(3) + th_id(04d) + suffix
# E.g. "99995430126189" -> vervar=9999, var=543, th=0126, suffix=189
# 1 point per year (annual value)

_KEY_RE_543 = re.compile(r"^\d{12,14}$")


def validate_tpt(responses: list[BpsVarResponse]) -> list[tuple[int, int, Decimal]]:
    """Validate TPT responses. Returns [(year, th_id, value)]."""
    result: list[tuple[int, int, Decimal]] = []
    for raw in responses:
        body = raw.body
        payload = BpsMacroRawResponse.model_validate(body)
        if payload.data_availability != "available":
            raise ValueError(
                f"BPS TPT 'data-availability' = {payload.data_availability!r}"
            )
        year = _extract_year(payload)
        th_id = _extract_th_id(payload)
        if year is None or th_id is None:
            raise ValueError("Respons BPS tidak punya tahun[0] yang valid")
        dc = _parse_datacontent_values(payload.datacontent)
        th_candidates = [f"{th_id:04d}", f"{th_id:03d}", str(th_id)]
        for key, value in dc.items():
            if not _KEY_RE_543.match(key):
                raise ValueError(f"Key datacontent TPT tidak dikenali: {key!r}")
            found = False
            for th_str in th_candidates:
                idx = key.rfind(th_str)
                if idx >= 0:
                    suffix = key[idx + len(th_str):]
                    if suffix.isdigit():
                        found = True
                        break
            if not found:
                raise ValueError(f"Key TPT {key!r} tidak mengandung th_id {th_id}")
            result.append((year, th_id, value))
        if not dc:
            raise ValueError(f"TPT datacontent kosong untuk th_id {th_id}")
    return result


# --- Foreign reserves (var 1091, vervar=8) ---
# Key format: vervar(1) + var(4) + th_id(04d) + suffix(1)
# E.g. "6109101250" -> vervar=6, var=1091, th=0125, suffix=0
# 1 point per year for total (vervar=8 = "Jumlah")
# But vervar in the key is the component code (1-8), not the filter value
# We filter by vervar=8 in the URL, so the API only returns data for vervar=8

def validate_foreign_reserves(responses: list[BpsVarResponse]) -> list[tuple[int, int, Decimal]]:
    """Validate foreign reserves responses. Returns [(year, th_id, value)]."""
    result: list[tuple[int, int, Decimal]] = []
    for raw in responses:
        body = raw.body
        payload = BpsMacroRawResponse.model_validate(body)
        if payload.data_availability != "available":
            raise ValueError(
                f"BPS foreign reserves 'data-availability' = {payload.data_availability!r}"
            )
        year = _extract_year(payload)
        th_id = _extract_th_id(payload)
        if year is None or th_id is None:
            raise ValueError("Respons BPS tidak punya tahun[0] yang valid")
        dc = _parse_datacontent_values(payload.datacontent)
        if not dc:
            raise ValueError(f"Foreign reserves datacontent kosong untuk th_id {th_id}")
        # Should be exactly 1 key for vervar=8 (total)
        for key, value in dc.items():
            result.append((year, th_id, value))
    return result
