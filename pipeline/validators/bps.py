"""Pydantic validation of raw BPS Web API responses.

The BPS "list model data" endpoint returns a JSON object, not an array. Its
`datacontent` is a flat mapping whose keys encode month so we can decode
observations, and whose values are strings (e.g. "113.98").

Validation contract (ARCHITECTURE.md 4): if the raw response does not match the
expected shape, raise -- never let malformed data reach the transformer.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator

# key = vervar (4) + var (variable) + th_id (4, zero-padded) + month (1..12);
# month is never zero-padded. Because var width varies (var 2 vs var 1709) and
# month can end in two digits, greedy tail-guessing is ambiguous (e.g. "01211"
# is th=0121+month=1, not th=012+month=11). So month is derived by anchoring on
# the known th_id: strip the fixed th_id, whatever follows is exactly the month.
_DATACONTENT_KEY_RE = re.compile(r"^\d+(1[0-2]|[1-9])$")
_DATACONTENT_KEY_LEN_MIN = 4 + 1 + 4 + 1  # 10


def decode_datacontent_key(key: str, th_id: int) -> tuple[int, int]:
    """Return (th_id, month) from a BPS `datacontent` key.

    `th_id` is the expected period id for the response being parsed (from the
    `tahun` block). cf. the comment above: this is the only parse that is
    unambiguous across BPS's key shapes.
    """
    if len(key) < _DATACONTENT_KEY_LEN_MIN:
        raise ValueError(f"Key datacontent BPS tidak lengkap: {key!r}")

    th_str = f"{th_id:04d}"
    idx = key.rfind(th_str)
    if idx < 0:
        raise ValueError(
            f"Key datacontent BPS tidak mengandung th_id {th_id}: {key!r}"
        )
    month_str = key[idx + len(th_str):]
    if not month_str or not month_str.isdigit():
        raise ValueError(
            f"Bagian bulan di key datacontent BPS tidak valid: {key!r}"
        )
    month = int(month_str)
    if month < 1 or month > 12:
        raise ValueError(
            f"Bulan di key datacontent BPS di luar 1-12: {key!r} (bulan={month})"
        )
    return th_id, month


class BpsMonthObservation(BaseModel):
    """One decodable IHK value from a raw `datacontent` entry."""

    th_id: int
    month: int = Field(ge=1, le=12)
    value: Decimal


class BpsYearData(BaseModel):
    """Validated raw data for one served year (th_id present, months parsed)."""

    year: int
    th_id: int
    observations: list[BpsMonthObservation] = Field(default_factory=list)


class BpsRawResponse(BaseModel):
    """Top-level shape of one BPS API response."""

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


def validate_years(responses: list[object]) -> list[BpsYearData]:
    """Validate fetch output (list of BpsYearResponse) into per-year data.

    Raises ValueError (via Pydantic ValidationError or explicit check) on any
    response that does not match the expected BPS shape. Callers must NOT
    proceed to transform with unvalidated input.
    """
    validated: list[BpsYearData] = []
    for raw in responses:
        body = getattr(raw, "body", raw)
        if not isinstance(body, dict):
            raise TypeError(f"Respons BPS harus dict, dapat: {type(body).__name__}")
        payload = BpsRawResponse.model_validate(body)
        if payload.data_availability != "available":
            raise ValueError(
                f"BPS 'data-availability' = {payload.data_availability!r}, bukan 'available'"
            )
        year = _extract_year(payload)
        if year is None:
            raise ValueError("Respons BPS tidak punya `tahun[0].label` yang valid")

        th_id = _extract_th_id_from_tahun(payload)
        if th_id is None:
            raise ValueError("Respons BPS tidak punya `tahun[0].val` (th_id)")

        obs: list[BpsMonthObservation] = []
        for key, raw_value in payload.datacontent.items():
            if not _DATACONTENT_KEY_RE.match(key):
                raise ValueError(f"Key datacontent BPS tidak dikenali: {key!r}")
            _, month = decode_datacontent_key(key, th_id)
            try:
                # str() to route statelessly; BPS may send "113.98" or 113.98.
                # float->str keeps the shortest round-trip repr, avoiding
                # binary-float artifacts when Decimal is built directly.
                value = Decimal(str(raw_value))
            except InvalidOperation as exc:
                raise ValueError(
                    f"Nilai non-numerik di datacontent BPS, key={key!r} value={raw_value!r}"
                ) from exc
            obs.append(BpsMonthObservation(th_id=th_id, month=month, value=value))

        if len({o.th_id for o in obs}) > 1:
            raise ValueError(
                f"th_id campur dalam satu respons tahun ({sorted({o.th_id for o in obs})})"
            )

        validated.append(BpsYearData(year=year, th_id=th_id, observations=obs))
    return validated


def _extract_year(payload: BpsRawResponse) -> int | None:
    if not payload.tahun or "label" not in payload.tahun[0]:
        return None
    try:
        return int(payload.tahun[0]["label"])
    except (TypeError, ValueError):
        return None


def _extract_th_id_from_tahun(payload: BpsRawResponse) -> int | None:
    if not payload.tahun or "val" not in payload.tahun[0]:
        return None
    try:
        return int(payload.tahun[0]["val"])
    except (TypeError, ValueError):
        return None