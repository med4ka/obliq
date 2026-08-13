"""Yahoo Finance v8 chart fetcher for Indonesian equities/indices (IHSG ^JKSE).

WHAT it fetches: daily OHLC + volume + adjusted close for a single symbol from
Yahoo Finance's v8 chart endpoint:
    https://query1.finance.yahoo.com/v8/finance/chart/{symbol}
Validated LIVE in Sesi 28 and re-verified before Sesi 29 implementation:
IHSG = `^JKSE` (currency IDR, exchangeTimezoneName "Asia/Jakarta", ~6.241 daily
bars 2000-2024), individual stocks = `CODE.JK` (e.g. BBCA.JK).

IMPORTANT -- this is NOT an official Yahoo API. It is the public endpoint the
Yahoo website itself uses, so:
  - there is no SLA and no documented rate limit (RULES.md 1);
  - the JSON shape can change or the endpoint can start blocking us without
    notice;
  - we MUST be polite: honest User-Agent, one request at a time with a minimum
    inter-request gap, timeout + retry with exponential backoff, and never a
    burst of requests (SYSTEM.md 1.6).

Response shape (verified live): chart.result[0] contains
  - meta:  { currency, symbol, fullExchangeName, exchangeTimezoneName, ... }
  - timestamp: [unix seconds] -- one entry per daily bar
  - indicators.quote[0]:   { open[], high[], low[], close[], volume[] }
  - indicators.adjclose[0]: { adjclose[] }   <-- key is "adjclose", NOT "close"
The arrays are parallel: index i of each list belongs to timestamp[i].
Any quote value may be null (e.g. no open on a suspended/half day).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3
MIN_REQUEST_INTERVAL_SECONDS = 1.0  # polite pacing toward Yahoo (RULES.md 1)

# Honest identification (SYSTEM.md 1.6). Yahoo sometimes returns a generic
# stock page when the UA looks like a bot; this is still truthful.
UA = "Obliq/0.1 (data pipeline; https://github.com/yourorg/obliq; research@example.com)"

# Latest bar for `^JKSE` (2026-08-11) was confirmed to be the current day's
# session, so `end_date` defaults to today; the transformer derives the
# observation date in Asia/Jakarta (index values are the same date either way).
DEFAULT_RANGE_DAYS = 90  # "mulai dengan rentang kecil" -- Sesi 29 rule

_last_request_at = 0.0


class YahooFetchError(RuntimeError):
    """A Yahoo fetch failed permanently after all retries (no silent gap)."""


@dataclass(frozen=True)
class YahooChartResponse:
    """One raw chart response (full JSON body) plus the symbol it was for."""

    symbol: str
    start: date
    end: date
    body: dict[str, Any]
    fetched_at: datetime


def _throttle() -> None:
    """Keep at least MIN_REQUEST_INTERVAL_SECONDS between requests to Yahoo.

    Module-level so repeated fetch() calls inside one process never hammer the
    endpoint (RULES.md 1: don't over-fetch even though it technically works).
    """
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def _to_unix_midnight(d: date) -> int:
    """Midnight UTC of `d` as unix seconds (Yahoo period1/period2 convention).

    The live bars for ^JKSE are timestamped at 00:00 UTC, so this matches the
    source's own convention; the transformer re-interprets them as exchange
    dates via Asia/Jakarta.
    """
    return int(datetime.combine(d, dtime.min, tzinfo=timezone.utc).timestamp())


def _fetch_json(symbol: str, params: dict[str, str | int]) -> dict[str, Any]:
    last_error: Exception | None = None
    url = YAHOO_CHART_URL.format(symbol=symbol)
    for attempt in range(RETRY_ATTEMPTS):
        _throttle()
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": UA, "Accept": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
            if not isinstance(body, dict):
                raise YahooFetchError(
                    f"Respons Yahoo bukan object JSON: {type(body).__name__}"
                )
            return body
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "Yahoo fetch gagal (attempt %d/%d) symbol=%s: %s -- retry in %ss",
                attempt + 1,
                RETRY_ATTEMPTS,
                symbol,
                exc,
                wait,
            )
            time.sleep(wait)
    raise YahooFetchError(
        f"Yahoo fetch gagal setelah {RETRY_ATTEMPTS} percobaan untuk {symbol}: {last_error}"
    )


def fetch(
    symbol: str = "^JKSE",
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> YahooChartResponse:
    """Fetch daily OHLC/volume/adjclose for `symbol` over [start_date, end_date].

    Defaults to the last DEFAULT_RANGE_DAYS calendar days (small range -- Sesi 29
    rule: validate end-to-end before any full backfill). Yahoo's period2 is
    exclusive, so we request end_date + 1 day to include the end date's bar.

    Returns a raw YahooChartResponse; callers MUST validate before transform
    (ARCHITECTURE.md 4). Raises YahooFetchError after retries -- no silent gap.
    """
    end = end_date or date.today()
    start = start_date or end - timedelta(days=DEFAULT_RANGE_DAYS)
    if start > end:
        raise ValueError(f"start_date {start} lebih baru dari end_date {end}")

    params: dict[str, str | int] = {
        "period1": _to_unix_midnight(start),
        "period2": _to_unix_midnight(end + timedelta(days=1)),
        "interval": "1d",
        "includeAdjustedClose": "true",
        "events": "div,splits",
    }
    body = _fetch_json(symbol, params)
    return YahooChartResponse(
        symbol=symbol,
        start=start,
        end=end,
        body=body,
        fetched_at=datetime.now(),
    )


@dataclass
class MultiFetchResult:
    """Result of fetching multiple symbols sequentially."""

    responses: list[YahooChartResponse]
    errors: list[tuple[str, str]]  # (symbol, error_message)


def fetch_multi(
    symbols: list[str],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MultiFetchResult:
    """Fetch multiple symbols sequentially with polite pacing.

    Each symbol is fetched independently. Failing symbols are collected in
    `.errors` -- the function never aborts on a single failure (SYSTEM.md 3:
    no silent gaps, one source must not brick the batch).
    """
    responses: list[YahooChartResponse] = []
    errors: list[tuple[str, str]] = []
    for sym in symbols:
        try:
            resp = fetch(symbol=sym, start_date=start_date, end_date=end_date)
            responses.append(resp)
        except Exception as exc:  # noqa: BLE001 -- collect, never abort
            msg = f"{type(exc).__name__}: {exc}"
            logger.error("Yahoo multi-fetch: %s gagal -- %s", sym, msg)
            errors.append((sym, msg))
    return MultiFetchResult(responses=responses, errors=errors)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raw = fetch()
    result = raw.body.get("chart", {}).get("result") or []
    n = len(result[0]["timestamp"]) if result else 0
    print(f"Fetched {raw.symbol} [{raw.start}..{raw.end}]: {n} bars, HTTP JSON OK.")
