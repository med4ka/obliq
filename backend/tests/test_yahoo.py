"""Tests for Yahoo Finance v8 pipeline (fetcher-independent logic).

Covers the two mandatory minimum tests from RULES.md 2:
  1. Transform produces correct StockObservation values from sample data.
  2. Validator rejects malformed responses (wrong shape, missing keys).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from pipeline.transformers.yahoo import StockObservation, transform
from pipeline.validators.yahoo import (
    YahooChartData,
    YahooMeta,
    YahooQuoteData,
    validate_chart,
)


def _make_validated(
    *,
    symbol: str = "^JKSE",
    currency: str = "IDR",
    timestamps: list[int] | None = None,
    opens: list[float | None] | None = None,
    highs: list[float | None] | None = None,
    lows: list[float | None] | None = None,
    closes: list[float | None] | None = None,
    volumes: list[int | None] | None = None,
    adjcloses: list[float | None] | None = None,
) -> YahooChartData:
    n = len(timestamps) if timestamps else 0
    return YahooChartData(
        symbol=symbol,
        meta=YahooMeta(currency=currency, symbol=symbol),
        timestamp=timestamps or [],
        quote=YahooQuoteData(
            open=opens or [None] * n,
            high=highs or [None] * n,
            low=lows or [None] * n,
            close=closes or [None] * n,
            volume=volumes or [None] * n,
        ),
        adjclose=adjcloses,
    )


_SAMPLE_TS = [1609459200, 1609545600, 1609632000]  # 2021-01-01..03 UTC


class TestTransform:
    def test_ohlc_adjclose_parsed_correctly(self) -> None:
        data = _make_validated(
            timestamps=_SAMPLE_TS,
            opens=[6200.5, 6210.0, 6190.0],
            highs=[6250.0, 6230.5, 6210.0],
            lows=[6180.0, 6195.0, 6175.0],
            closes=[6230.0, 6205.75, 6195.5],
            volumes=[1_500_000_000, 1_300_000_000, 1_200_000_000],
            adjcloses=[6230.0, 6205.75, 6195.5],
        )
        obs = transform(data)
        assert len(obs) == 3

        assert obs[0].observation_date == date(2021, 1, 1)
        assert obs[0].open == Decimal("6200.5")
        assert obs[0].high == Decimal("6250.0")
        assert obs[0].low == Decimal("6180.0")
        assert obs[0].close == Decimal("6230.0")
        assert obs[0].adj_close == Decimal("6230.0")
        assert obs[0].volume == 1_500_000_000

        assert obs[1].observation_date == date(2021, 1, 2)
        assert obs[1].close == Decimal("6205.75")
        assert obs[1].adj_close == Decimal("6205.75")

    def test_null_quote_values_become_none(self) -> None:
        data = _make_validated(
            timestamps=_SAMPLE_TS[:1],
            opens=[None],
            highs=[None],
            lows=[None],
            closes=[6300.0],
            volumes=[None],
            adjcloses=[6300.0],
        )
        obs = transform(data)
        assert len(obs) == 1
        assert obs[0].open is None
        assert obs[0].high is None
        assert obs[0].low is None
        assert obs[0].volume is None
        assert obs[0].close == Decimal("6300.0")

    def test_null_close_skipped(self) -> None:
        data = _make_validated(
            timestamps=_SAMPLE_TS,
            closes=[6300.0, None, 6310.0],
            volumes=[100, 200, 300],
        )
        obs = transform(data)
        assert len(obs) == 2  # middle bar skipped
        assert obs[0].close == Decimal("6300.0")
        assert obs[1].close == Decimal("6310.0")

    def test_no_adjclose_list_means_none(self) -> None:
        data = _make_validated(
            timestamps=_SAMPLE_TS[:1],
            closes=[6300.0],
            adjcloses=None,
        )
        obs = transform(data)
        assert obs[0].adj_close is None

    def test_decimal_precision_preserved(self) -> None:
        """Binary float artifacts like 6338.5908203125 must round-trip cleanly."""
        data = _make_validated(
            timestamps=_SAMPLE_TS[:1],
            closes=[6338.5908203125],
            adjcloses=[6338.5908203125],
        )
        obs = transform(data)
        assert obs[0].close == Decimal("6338.5908203125")
        assert obs[0].adj_close == Decimal("6338.5908203125")


class TestValidatorRejectsMalformed:
    def _chart_body(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "chart": {
                "result": [
                    {
                        "meta": {"currency": "IDR", "symbol": "^JKSE"},
                        "timestamp": [1609459200],
                        "indicators": {
                            "quote": [
                                {"open": [6200.0], "high": [6250.0], "low": [6180.0],
                                 "close": [6230.0], "volume": [1500000000]}
                            ],
                            "adjclose": [{"adjclose": [6230.0]}],
                        },
                    }
                ],
                "error": None,
            }
        }
        base.update(overrides)
        return base

    def test_tolak_tanpa_chart_key(self) -> None:
        with pytest.raises(ValueError, match="tidak punya key 'chart'"):
            validate_chart({"foo": "bar"})

    def test_tolak_chart_error(self) -> None:
        body = self._chart_body()
        body["chart"]["error"] = "Not Found"
        with pytest.raises(ValueError, match="Yahoo mengembalikan error"):
            validate_chart(body)

    def test_tolak_result_kosong(self) -> None:
        body = self._chart_body()
        body["chart"]["result"] = []
        with pytest.raises(ValueError, match="chart.result Yahoo kosong"):
            validate_chart(body)

    def test_tolak_timestamp_kosong(self) -> None:
        body = self._chart_body()
        body["chart"]["result"][0]["timestamp"] = []
        with pytest.raises(ValidationError):
            validate_chart(body)

    def test_tolak_quote_arrays_tidak_sama_panjang(self) -> None:
        body = self._chart_body()
        body["chart"]["result"][0]["indicators"]["quote"][0]["open"] = [6200.0, 6210.0]
        with pytest.raises(ValidationError, match="tidak seragam"):
            validate_chart(body)

    def test_tolak_adjclose_panjang_tidak_sama(self) -> None:
        body = self._chart_body()
        body["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"] = [6230.0, 6240.0]
        with pytest.raises(ValidationError, match="adjclose Yahoo != panjang close"):
            validate_chart(body)
