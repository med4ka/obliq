"""BPS (Badan Pusat Statistik) multi-indicator fetcher.

WHAT it fetches: economic indicators from the official BPS Web API:
    https://webapi.bps.go.id/v1/api

Originally for IHK inflation (var 1709, Sesi 6), now extended with 4 new
macro indicators (Sesi 44) -- each documented below:

  IHK consumer price index:
    var=1709, vervar=9999 (national), monthly. Year range: 2020-2023.

  Trade balance (Nilai Neraca Perdagangan):
    var=498, vervar=9999 (Indonesia), monthly. Year range: 2017-2026.

  PDB growth (Laju Pertumbuhan PDB Seri 2010):
    var=104, turvar=5 (y-on-y), vervar=99003 (PDB total), quarterly.
    Year range: 2011-2026.

  TPT (Tingkat Pengangguran Terbuka):
    var=543, vervar=9999 (INDONESIA), annual. Year range: up to 2026.

  Foreign reserves (Posisi Cadangan Devisa):
    var=1091, vervar=8 (Jumlah/total), annual. Year range: 2016-2025.

th_id (period id) per var is fetched dynamically from the API's own th list,
because different vars have different th_id->year mappings.
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

REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3

UA = "Obliq/0.1 (data pipeline; https://github.com/yourorg/obliq; research@example.com)"


@dataclass(frozen=True)
class BpsVarResponse:
    """One raw API response for a single var/year pair."""

    var: str
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


def _fetch_th_list(var: str) -> dict[int, int]:
    """Fetch {year: th_id} mapping from the API for a given var.

    Th rows are keyed 'th' (year label) and 'th_id' (numeric id). Iterates
    pages until all are consumed.
    """
    api_key = _get_api_key()
    page = 1
    mapping: dict[int, int] = {}
    while True:
        url = (
            f"{BPS_BASE_URL}/list/model/th/lang/ind/domain/{BPS_DOMAIN}"
            f"/var/{var}/key/{api_key}?page={page}&per_page=50"
        )
        r = requests.get(url, timeout=15, headers={"User-Agent": UA, "Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            break
        d = data["data"]
        pagination = d[0]
        records = d[1]
        for item in records:
            th_year = item.get("th")
            th_id = item.get("th_id")
            if th_year and th_id:
                mapping[int(th_year)] = int(th_id)
        if page >= pagination["pages"]:
            break
        page += 1
    return mapping


def _fetch_var(
    api_key: str,
    var: str,
    year: int,
    th_id: int,
    vervar: str | None = None,
    turvar: str | None = None,
) -> BpsVarResponse:
    """Fetch one var/year from the BPS API, with optional vervar/turvar."""
    url = f"{BPS_BASE_URL}/list/model/data/lang/ind/domain/{BPS_DOMAIN}/var/{var}/th/{th_id}/key/{api_key}"
    if vervar:
        url += f"/vervar/{vervar}"
    if turvar:
        url += f"/turvar/{turvar}"

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
            return BpsVarResponse(var=var, year=year, th_id=th_id, body=body)
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "BPS fetch gagal (attempt %d/%d) var=%s year=%s th_id=%s: %s -- retry in %ss",
                attempt + 1, RETRY_ATTEMPTS, var, year, th_id, exc, wait,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"BPS fetch gagal setelah {RETRY_ATTEMPTS} percobaan untuk var={var} year={year}: {last_error}"
    )


def _fetch_var_years(
    var: str,
    vervar: str | None = None,
    turvar: str | None = None,
    years: list[int] | None = None,
) -> list[BpsVarResponse]:
    """Fetch a BPS var across years, optionally restricted to given years."""
    api_key = _get_api_key()
    year_to_th = _fetch_th_list(var)
    if years:
        requested = {y for y in years if y in year_to_th}
    else:
        requested = set(year_to_th)
    responses: list[BpsVarResponse] = []
    for year in sorted(requested):
        responses.append(_fetch_var(api_key, var, year, year_to_th[year], vervar=vervar, turvar=turvar))
    return responses


# --- IHK (original, unchanged interface) ---

BPS_VAR_IHK = "1709"
BPS_VERVAR_NASIONAL = "9999"

YEAR_TO_TH_ID: dict[int, int] = {2020: 120, 2021: 121, 2022: 122, 2023: 123}


def _list_th_ids() -> dict[int, int]:
    return dict(YEAR_TO_TH_ID)


def fetch_years_detected() -> list[int]:
    return sorted(_list_th_ids())


def _fetch_year(api_key: str, year: int, th_id: int) -> BpsVarResponse:
    return _fetch_var(api_key, BPS_VAR_IHK, year, th_id, vervar=BPS_VERVAR_NASIONAL)


def fetch(years: list[int] | None = None) -> list[BpsVarResponse]:
    """Fetch monthly IHK for every year the API currently serves (2020-2023)."""
    api_key = _get_api_key()
    year_to_th = _list_th_ids()
    if years:
        requested = {y for y in years if y in year_to_th}
    else:
        requested = set(year_to_th)
    responses: list[BpsVarResponse] = []
    for year in sorted(requested):
        responses.append(_fetch_year(api_key, year, year_to_th[year]))
    return responses


# --- New indicator fetch functions ---

def fetch_trade_balance(years: list[int] | None = None) -> list[BpsVarResponse]:
    """Fetch monthly trade balance (Nilai Neraca Perdagangan, var=498).

    var=498, vervar=9999 (Indonesia), monthly (13 pts/year: 12 months + annual).
    Year range: 2017-2026.
    """
    return _fetch_var_years("498", vervar="9999", years=years)


def fetch_pdb_growth(years: list[int] | None = None) -> list[BpsVarResponse]:
    """Fetch quarterly PDB growth y-on-y (var=104, turvar=5).

    var=104 (Seri 2010 Laju Pertumbuhan PDB), turvar=5 (y-on-y),
    vervar=99003 (PRODUK DOMESTIK BRUTO / national total).
    Year range: 2011-2026.
    """
    return _fetch_var_years("104", vervar="99003", turvar="5", years=years)


def fetch_tpt(years: list[int] | None = None) -> list[BpsVarResponse]:
    """Fetch national TPT (Tingkat Pengangguran Terbuka, var=543).

    var=543 (by province), vervar=9999 (INDONESIA / national aggregate).
    Annual data. Year range: up to 2026.
    """
    return _fetch_var_years("543", vervar="9999", years=years)


def fetch_foreign_reserves(years: list[int] | None = None) -> list[BpsVarResponse]:
    """Fetch foreign reserves (Posisi Cadangan Devisa total, var=1091).

    var=1091, vervar=8 (Jumlah / total). Annual data.
    Year range: 2016-2025.
    """
    return _fetch_var_years("1091", vervar="8", years=years)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    targets = {
        "ihk": ("IHK", fetch),
        "trade": ("Trade Balance", fetch_trade_balance),
        "pdb": ("PDB Growth", fetch_pdb_growth),
        "tpt": ("TPT", fetch_tpt),
        "reserves": ("Foreign Reserves", fetch_foreign_reserves),
    }
    if target == "all":
        for label, fn in targets.values():
            data = fn()
            total = sum(len(r.body.get("datacontent", {})) for r in data)
            print(f"{label}: {len(data)} years, {total} raw observations")
    elif target in targets:
        label, fn = targets[target]
        data = fn()
        total = sum(len(r.body.get("datacontent", {})) for r in data)
        print(f"{label}: {len(data)} years, {total} raw observations")
    else:
        print(f"Unknown target {target!r}. Choose from: {', '.join(targets)}")