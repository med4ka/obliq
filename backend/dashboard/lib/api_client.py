"""Read-only client for the Obliq FastAPI layer.

The dashboard NEVER touches the database or external sources directly
(ARCHITECTURE.md 1). Every number shown comes from an API response, which is
the single consumer-facing gateway over the database.

Consumer-facing helpers:
    current_curve()      -> GET  /api/yield-curve/current
    bond_history(code)   -> GET  /api/yield-curve/history?bond_code=...
    macro_latest()       -> GET  /api/macro/latest
    macro_history(type)  -> GET  /api/macro/{indicator_type}

Each returns a plain dict (status/message/count + parsed items) so the UI layer
only handles presentation. API decimals arrive as exact strings (schemas.py
serializer) -- they are parsed to float here for plotting; display formatting
is a separate concern (styling.py).
"""
from __future__ import annotations

import os

import requests  # already a core dependency (requirements.txt)

DEFAULT_BASE_URL = "http://127.0.0.1:8000"

# Overridable with OBLIQ_API_BASE_URL so the dashboard can point anywhere.
API_BASE_URL = os.getenv("OBLIQ_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

REQUEST_TIMEOUT_SECONDS = 15.0


class ApiClientError(Exception):
    """Raised when the API is unreachable or returns an unexpected payload."""


def _get(path: str, **params) -> dict:
    """GET one endpoint, returning parsed JSON. Raises ApiClientError on failure."""
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ApiClientError(
            f"API tidak bisa dijangkau ({url}). Pastikan `uvicorn api.main:app` "
            f"sedang berjalan. Detail: {exc}"
        ) from exc
    if resp.status_code != 200:
        raise ApiClientError(
            f"API mengembalikan status {resp.status_code} untuk {url}."
        )
    try:
        payload = resp.json()
    except ValueError as exc:
        raise ApiClientError(f"Respons API tidak valid JSON dari {url}.") from exc
    if not isinstance(payload, dict):
        raise ApiClientError(f"Respons API tidak berbentuk objek dari {url}.")
    return payload


def _to_float(value) -> float | None:
    """API decimals are exact strings; convert for plotting. None stays None."""
    if value is None:
        return None
    return float(str(value))


def current_curve() -> dict:
    """Latest yield per active bond (the 'current' government yield curve)."""
    payload = _get("/api/yield-curve/current")
    for item in payload.get("items", []):
        item["tenor_years"] = _to_float(item.get("tenor_years"))
        item["coupon_rate"] = _to_float(item.get("coupon_rate"))
        item["yield_value"] = _to_float(item.get("yield_value"))
        item["price"] = _to_float(item.get("price"))
    return payload


def bond_history(bond_code: str) -> dict:
    """Yield history of one bond code (e.g. FR0100)."""
    payload = _get("/api/yield-curve/history", bond_code=bond_code)
    for item in payload.get("items", []):
        item["yield_value"] = _to_float(item.get("yield_value"))
        item["price"] = _to_float(item.get("price"))
    return payload


def macro_latest() -> dict:
    """Most recent observation of every indicator type."""
    payload = _get("/api/macro/latest")
    for item in payload.get("items", []):
        item["value"] = _to_float(item.get("value"))
    return payload


def macro_history(indicator_type: str) -> dict:
    """Full history of one indicator (e.g. inflation_yoy)."""
    payload = _get(f"/api/macro/{indicator_type}")
    for item in payload.get("items", []):
        item["value"] = _to_float(item.get("value"))
    return payload