"""BPS (Badan Pusat Statistik) IHK fetcher.

WHAT it fetches: monthly Indonesia IHK (Indeks Harga Konsumen / consumer price
index), national aggregate, direct from the official BPS Web API:
    https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/{id}/th/{th_id}/key/{KEY}/vervar/{vervar}
(BPS's public JSON API -- the same endpoint the BPS site's own tools use.)

WHY this var/vervar combination (validated against the live API):
  - var_id = 1709  -> "Indeks Harga Konsumen 90 Kota (Umum)", basis 2018=100.
    This is the CURRENT official IHK series (the National CPI after the 2018
    rebasing to 90 cities). var_id=2 ("Indeks Harga Konsumen Umum") is the OLD
    series (basis 2012) and BPS only serves it for 1979-2019, so it is NOT used.
  - vervar = 9999  -> "INDONESIA", the national aggregate over all cities.
  - domain  = 0000 -> national level.

WHY per-year requests instead of a range: the API rejects a `th` range like
th/2023:2025 (returns "list-not-available"); a valid value is ONE th_id (period
data id) per year. th_id is not the calendar year -- e.g. 2023 = th_id 123,
2022 = 122 (via the API's own year/mapping list). Each monthly value arrives in
`datacontent` keyed `{vervar}{var}{th_id:04d}{month}`, so the raw JSON is not
directly usable YOY data -- BPS computes MtM inflation separately; YOY must be
derived in the transformer (see pipeline/transformers/bps.py).

Every HTTP call is honest: identifies itself with a real User-Agent, times out,
and retries with exponential backoff (SYSTEM.md 3). Key comes from .env;
never hardcode it.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BPS_BASE_URL = "https://webapi.bps.go.id/v1/api"
BPS_DOMAIN = "0000"
BPS_VAR_IHK = "1709"  # IHK 90 Kota, Umum, basis 2018=100 (national CPI)
BPS_VERVAR_NASIONAL = "9999"  # "INDONESIA"

# th_id (API period id) -> year. Determined from the API's own th list and
# expected to need extending when BPS publishes a newer year. (2024+ are not
# yet served by the API for this var.)
YEAR_TO_TH_ID: dict[int, int] = {2020: 120, 2021: 121, 2022: 122, 2023: 123}

REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3  # first backoff; doubles per retry

# Distinct per content type so the API key (a secret) and the payload stay
# separable in logs.
UA = "Obliq/0.1 (data pipeline; https://github.com/yourorg/obliq; research@example.com)"


@dataclass(frozen=True)
class BpsYearResponse:
    """One raw API response for a single calendar year."""

    year: int
    th_id: int
    body: dict[str, Any]


def _get_api_key() -> str:
    key = os.getenv("BPS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "BPS_API_KEY tidak ada di .env. Isi dengan key dari webapi.bps.go.id "
            "(lihat PROGRESS.md 'Diketahui Bermasalah')."
        )
    return key


def _list_th_ids() -> dict[int, int]:
    """Return {year: th_id} as reported by the API, for supported years."""
    return dict(YEAR_TO_TH_ID)


def fetch_years_detected() -> list[int]:
    """Years BPS currently serves for this IHK var (used to size the fetch)."""
    return sorted(_list_th_ids())


def _fetch_year(api_key: str, year: int, th_id: int) -> BpsYearResponse:
    url = (
        f"{BPS_BASE_URL}/list/model/data/lang/ind/domain/{BPS_DOMAIN}"
        f"/var/{BPS_VAR_IHK}/th/{th_id}/key/{api_key}/vervar/{BPS_VERVAR_NASIONAL}"
    )
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = requests.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": UA, "Accept": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
            if not isinstance(body, dict):
                raise ValueError(f"BPS response bukan object JSON: {type(body).__name__}")
            return BpsYearResponse(year=year, th_id=th_id, body=body)
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "BPS fetch gagal (attempt %d/%d), year=%s th_id=%s: %s -- retry in %ss",
                attempt + 1,
                RETRY_ATTEMPTS,
                year,
                th_id,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"BPS fetch gagal setelah {RETRY_ATTEMPTS} percobaan untuk {year}: {last_error}")


def fetch(years: list[int] | None = None) -> list[BpsYearResponse]:
    """Fetch monthly IHK for every year the API currently serves (2020-2023).

    `years` optionally restricts the fetch to a small range (e.g. the latest
    year only, for the scheduler's incremental runs). Unsupported years are
    silently skipped. Defaults to all served years.

    Returns one BpsYearResponse per fetched year. Raises RuntimeError if any
    year's fetch fails after retries -- no silent gaps (SYSTEM.md 3).
    """
    api_key = _get_api_key()
    year_to_th = _list_th_ids()
    if years:
        requested = {y for y in years if y in year_to_th}
    else:
        requested = set(year_to_th)
    responses: list[BpsYearResponse] = []
    for year in sorted(requested):
        responses.append(_fetch_year(api_key, year, year_to_th[year]))
    return responses


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    years: list[int] | None = None
    import sys
    if len(sys.argv) > 1:
        years = [int(a) for a in sys.argv[1:]]
    data = fetch(years)
    total = sum(len(r.body.get("datacontent", {})) for r in data)
    print(f"Fetched {len(data)} years, {total} raw observations (IHK var={BPS_VAR_IHK}).")