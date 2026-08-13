"""Bank Indonesia (BI) macroeconomic indicator fetcher: BI7DRR + JISDOR (USD/IDR).

WHAT it fetches: two official Bank Indonesia public datasets, both Sesi 15
validated live and APPROVED:

  - BI7DRR (BI 7-Day Reverse Repo Rate), the policy rate since April 2016:
        https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx
  - JISDOR (Jakarta Interbank Spot Dollar Rate), the daily USD/IDR reference
        https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx

HOW it works (validated in Sesi 15, do NOT re-research): the pages are ASP.NET
WebForms rendered server-side (no headless browser needed). Each page has a
period filter (Dari/Sampai) and an "Unduh" (export) button that is a normal
postback. A plain HTTP flow works:

    GET  page                            -> extract __VIEWSTATE/__VIEWSTATEGENERATOR/
                                            __EVENTVALIDATION from the HTML
    POST page (hidden tokens + date range + ButtonExport value)  -> REAL .xlsx bytes
                                            (application/vnd.openxmlformats-...)

JISDOR data exists from 2013-05-20 (2011-2012 export = empty); BI7DRR from
2016-04-21 (2000-2012 = empty, consistent with when the rate was launched).
The XLSX export is capped around ~3200 rows, so JISDOR is fetched per year.

Every HTTP call is honest (real User-Agent), times out, retries with
exponential backoff (SYSTEM.md 3), and sleeps between requests to stay polite
(RULES.md 1: robots.txt allows / but rate-limit anyway).
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime

import requests

logger = logging.getLogger(__name__)

JISDOR_URL = "https://www.bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx"
BI7DRR_URL = "https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx"

# WebPart control prefixes (verified in the saved raw HTML, Sesi 15).
JISDOR_WP = "ctl00$ctl54$g_f51e6b6d_47c5_4ff4_8105_27cbd1a2f52d$ctl00$"
BI7DRR_WP = "ctl00$ctl54$g_78f62327_0ad4_4bb8_b958_a315eccecc27$ctl00$"

REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3
POLITE_SLEEP_SECONDS = 1.0  # between consecutive requests to bi.go.id

# Earliest data observed in the Sesi 15 exports. Used to size/sanity the range.
JISDOR_EARLIEST_DATE = date(2013, 5, 20)
BI7DRR_EARLIEST_DATE = date(2016, 4, 21)

UA = "Obliq/0.1 (data pipeline; https://github.com/yourorg/obliq; research@example.com)"

_HIDDEN_TOKEN_NAMES = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")


class BiFetchError(RuntimeError):
    """A BI fetch step failed permanently after all retries (no silent gap)."""


@dataclass(frozen=True)
class BiExport:
    """One XLSX export requested from a BI page (raw bytes + provenance)."""

    indicator_type: str  # "bi_7drr" | "usd_idr"
    date_from: date
    date_to: date
    content_type: str
    filename: str
    xlsx_bytes: bytes
    fetched_at: datetime


def _headers() -> dict[str, str]:
    return {"User-Agent": UA, "Accept": "*/*"}


def _extract_inputs(html: str) -> dict[str, str]:
    """Extract {name: value} for every <input> in a WebForms page (own HTML)."""
    inputs: dict[str, str] = {}
    for tag in re.finditer(r"<input[^>]*>", html, re.IGNORECASE):
        text = tag.group(0)
        name_m = re.search(r'name="([^"]*)"', text)
        value_m = re.search(r'value="([^"]*)"', text)
        if name_m:
            inputs[name_m.group(1)] = value_m.group(1) if value_m else ""
    return inputs


def _fetch_export(url: str, extra_fields: dict[str, str]) -> tuple[str, str, bytes]:
    """GET hidden fields then POST the export, with retry + backoff.

    One attempt = a full GET (fresh VIEWSTATE) + POST. Each retry re-runs both
    because the old __VIEWSTATE may be stale by the time we retry
    (SYSTEM.md 3: timeout + retry; RULES.md: never improvise around a denied
    POST -- a non-XLSX reply raises BiFetchError and stops).
    """
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            session = requests.Session()
            session.headers.update(_headers())

            resp = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            html = resp.text

            inputs = _extract_inputs(html)
            tokens = {name: inputs.get(name, "") for name in _HIDDEN_TOKEN_NAMES}
            missing = [name for name, value in tokens.items() if not value]
            if missing:
                raise BiFetchError(
                    f"Hidden fields WebForms hilang di {url}: {missing} "
                    f"(VIEWSTATE expired / layout berubah? STOP, reviu manual)"
                )

            data: dict[str, str] = dict(tokens)
            data.update(extra_fields)

            post = session.post(url, data=data, timeout=REQUEST_TIMEOUT_SECONDS)
            post.raise_for_status()
            content_type = post.headers.get("Content-Type", "")
            filename = post.headers.get("Content-Disposition", "")
            if "spreadsheetml" not in content_type:
                raise BiFetchError(
                    f"Respons export {url} bukan XLSX (content-type={content_type!r}). "
                    f"Server tolak POST? VIEWSTATE expired / butuh cookie? STOP & reviu manual."
                )
            return content_type, filename, post.content
        except (requests.RequestException, BiFetchError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "BI export gagal (attempt %d/%d) url=%s: %s -- retry in %ss",
                attempt + 1, RETRY_ATTEMPTS, url, exc, wait,
            )
            time.sleep(wait)
    raise BiFetchError(f"BI export {url} gagal setelah {RETRY_ATTEMPTS} percobaan: {last_error}")


def _fmt_dmy(d: date) -> str:
    """dd/mm/yyyy as the BI pages' datepickers expect (Sesi 15)."""
    return d.strftime("%d/%m/%Y")


def fetch_bi7drr(start: date, end: date) -> BiExport:
    """Fetch BI7DRR for [start, end] in ONE export request. Returns raw XLSX."""
    fields = {
        f"{BI7DRR_WP}TextBoxDateStart": _fmt_dmy(start),
        f"{BI7DRR_WP}TextBoxDateEnd": _fmt_dmy(end),
        f"{BI7DRR_WP}ButtonExport": "Unduh",
    }
    content_type, filename, body = _fetch_export(BI7DRR_URL, fields)
    return BiExport(
        indicator_type="bi_7drr",
        date_from=start,
        date_to=end,
        content_type=content_type,
        filename=filename,
        xlsx_bytes=body,
        fetched_at=datetime.now(),
    )


def fetch_jisdor(start: date, end: date) -> BiExport:
    """Fetch JISDOR USD/IDR for [start, end] in ONE export request."""
    fields = {
        f"{JISDOR_WP}TextBoxFrom": _fmt_dmy(start),
        f"{JISDOR_WP}HiddenFieldDateFrom": _fmt_dmy(start),
        f"{JISDOR_WP}TextBoxDateTo": _fmt_dmy(end),
        f"{JISDOR_WP}HiddenFieldDateTo": _fmt_dmy(end),
        f"{JISDOR_WP}ButtonExport": "Unduh",
    }
    content_type, filename, body = _fetch_export(JISDOR_URL, fields)
    return BiExport(
        indicator_type="usd_idr",
        date_from=start,
        date_to=end,
        content_type=content_type,
        filename=filename,
        xlsx_bytes=body,
        fetched_at=datetime.now(),
    )


def fetch_jisdor_years(years: list[int]) -> list[BiExport]:
    """Fetch JISDOR one calendar year at a time (export is capped ~3200 rows).

    Polite pacing: a GET + POST per year, sleeping between years.
    """
    exports: list[BiExport] = []
    for i, year in enumerate(sorted(years)):
        exports.append(fetch_jisdor(date(year, 1, 1), date(year, 12, 31)))
        if i < len(years) - 1:
            time.sleep(POLITE_SLEEP_SECONDS)
    return exports


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    drr = fetch_bi7drr(BI7DRR_EARLIEST_DATE, date.today())
    print(f"BI7DRR export: {len(drr.xlsx_bytes)} bytes, {drr.filename!r}")
    j = fetch_jisdor(date(2016, 1, 1), date(2016, 12, 31))
    print(f"JISDOR 2016 export: {len(j.xlsx_bytes)} bytes, {j.filename!r}")