"""Yahoo v8 chart -> internal stock_observations transformer.

WHAT it produces: one StockObservation per daily bar, with prices as Decimal
(never float -- SYSTEM.md 1.5) and the observation date derived from the bar's
unix timestamp in the exchange timezone (Asia/Jakarta; IDX has no DST, so the
offset is a constant +07:00).

WHY str() round-trip for Decimal: the API sends binary floats (e.g.
6338.5908203125). Decimal(float) would embed the full binary expansion; going
through str() keeps the shortest round-trip representation (the exact same
approach as pipeline/validators/bps.py).

Adjusted close: Yahoo provides an `adjclose` array parallel to the bars. For the
IHSG index it currently equals close (no dividend adjustment for the index
series), and Yahoo may return an empty adjclose list for some ranges -- when it
does, we store adj_close = None rather than inventing a value (SYSTEM.md 1.1:
never fabricate). Null quote values (e.g. a half-day without an open) are
carried through as None.

Source is a storage-layer concern (SCHEMA.md: source + fetched_at are filled at
write time), so this module only yields the observable values + date.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from pipeline.validators.yahoo import YahooChartData

logger = logging.getLogger(__name__)

EXCHANGE_TZ = ZoneInfo("Asia/Jakarta")  # IDX exchange timezone (no DST)


@dataclass(frozen=True)
class StockObservation:
    """One normalized daily price observation for one stock/index (SCHEMA.md)."""

    observation_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    adj_close: Decimal | None
    volume: int | None


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    try:
        # str() round-trip avoids binary-float artifacts when building Decimal.
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"nilai harga Yahoo tidak valid: {value!r}") from exc


def _to_date(unix_ts: int) -> date:
    """Bar timestamp -> trading date in the IDX exchange timezone.

    Live ^JKSE bars are stamped 00:00 UTC (== 07:00 WIB, same calendar day), so
    Asia/Jakarta yields the correct trading date for every observed bar.
    """
    return datetime.fromtimestamp(unix_ts, tz=EXCHANGE_TZ).date()


def transform(validated: YahooChartData) -> list[StockObservation]:
    """Normalize a validated chart response into daily observations.

    `validated` must come from validate_chart (already enforced by the type).
    Prices become Decimal; timestamps become exchange dates; adj_close comes from
    the parallel adjclose array (None if Yahoo sent none for this range).
    """
    bars = len(validated.timestamp)
    close_arr = validated.quote.close
    open_arr = validated.quote.open
    high_arr = validated.quote.high
    low_arr = validated.quote.low
    volume_arr = validated.quote.volume
    adj_arr = validated.adjclose  # None when Yahoo returned no adjclose list

    observations: list[StockObservation] = []
    for i in range(bars):
        close_val = close_arr[i]
        if close_val is None:
            # A bar must have a close; otherwise the row is unusable. Skip and
            # log -- never fabricate a value (SYSTEM.md 1.1, no silent gaps).
            logger.warning(
                "Skip bar %s (%s): close null di posisi %d -- gap, tanpa interpolasi",
                validated.symbol,
                _to_date(validated.timestamp[i]),
                i,
            )
            continue
        adj_close = None
        if adj_arr is not None:
            adj_close = _to_decimal(adj_arr[i]) if i < len(adj_arr) else None
        observations.append(
            StockObservation(
                observation_date=_to_date(validated.timestamp[i]),
                open=_to_decimal(open_arr[i]),
                high=_to_decimal(high_arr[i]),
                low=_to_decimal(low_arr[i]),
                close=_to_decimal(close_val),
                adj_close=adj_close,
                volume=volume_arr[i],
            )
        )
    return observations
