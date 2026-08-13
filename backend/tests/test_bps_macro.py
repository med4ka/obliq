"""Tests for BPS macro indicator pipeline (var 498, 104, 543, 1091).

Covers:
  1. Validator rejects malformed responses
  2. Transform produces correct observation_date and value from sample data
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pipeline.fetchers.bps import BpsVarResponse
from pipeline.transformers.bps_macro import (
    transform_trade_balance,
    transform_pdb_growth,
    transform_tpt,
    transform_foreign_reserves,
)
from pipeline.validators.bps_macro import (
    validate_trade_balance,
    validate_pdb_growth,
    validate_tpt,
    validate_foreign_reserves,
)


def _make_response(
    tahun_val: int,
    tahun_label: str,
    datacontent: dict[str, str | float],
    var: str = "498",
) -> BpsVarResponse:
    return BpsVarResponse(
        var=var,
        year=int(tahun_label),
        th_id=tahun_val,
        body={
            "status": "OK",
            "data-availability": "available",
            "last_update": "2026-01-01",
            "tahun": [{"val": tahun_val, "label": tahun_label}],
            "datacontent": datacontent,
        },
    )


# --- Trade balance (var 498) ---

class TestTradeBalance:
    def test_valid_monthly_data(self) -> None:
        dc = {f"9999498{124:04d}{m}": f"{100 + m}.0" for m in range(1, 13)}
        resp = _make_response(124, "2024", dc)
        validated = validate_trade_balance([resp])
        assert len(validated) == 12
        jan = next(v for v in validated if v[2] == 1)
        assert jan[3] == Decimal("101.0")

    def test_annual_total_row_skipped(self) -> None:
        """Monthly data with annual total (month=13) -> total skipped."""
        dc = {f"9999498{124:04d}{m}": "100.0" for m in range(1, 13)}
        dc[f"9999498{124:04d}13"] = "1200.0"
        resp = _make_response(124, "2024", dc)
        validated = validate_trade_balance([resp])
        transformed = transform_trade_balance(validated)
        assert len(transformed) == 12
        assert all(r.indicator_type == "trade_balance" for r in transformed)

    def test_observation_date_last_day_of_month(self) -> None:
        dc = {f"9999498{124:04d}6": "150.0"}
        resp = _make_response(124, "2024", dc)
        validated = validate_trade_balance([resp])
        transformed = transform_trade_balance(validated)
        assert transformed[0].observation_date == date(2024, 6, 30)

    def test_reject_availability_not_available(self) -> None:
        resp = BpsVarResponse(var="498", year=2024, th_id=124, body={
            "status": "OK",
            "data-availability": "list-not-available",
            "tahun": [{"val": 124, "label": "2024"}],
            "datacontent": {},
        })
        with pytest.raises(ValueError, match="data-availability"):
            validate_trade_balance([resp])


# --- PDB growth (var 104) ---

class TestPdbGrowth:
    def test_valid_quarterly_data(self) -> None:
        dc = {f"99003104{126:04d}{q}": f"{(q % 10) + 5}.0" for q in [31, 32, 33, 34]}
        resp = BpsVarResponse(var="104", year=2026, th_id=126, body={
            "status": "OK",
            "data-availability": "available",
            "tahun": [{"val": 126, "label": "2026"}],
            "datacontent": dc,
        })
        validated = validate_pdb_growth([resp])
        assert len(validated) == 4
        transformed = transform_pdb_growth(validated)
        assert len(transformed) == 4
        assert all(r.indicator_type == "pdb_yoy" for r in transformed)
        # Check quarter mapping: 31->Q1, 32->Q2, etc.
        q1 = next(r for r in transformed if r.observation_date == date(2026, 3, 31))
        assert q1.value == Decimal("6.0")  # 5.0 + 1

    def test_observation_date_last_day_of_quarter(self) -> None:
        dc = {f"99003104{126:04d}33": "4.56"}
        resp = BpsVarResponse(var="104", year=2026, th_id=126, body={
            "status": "OK",
            "data-availability": "available",
            "tahun": [{"val": 126, "label": "2026"}],
            "datacontent": dc,
        })
        validated = validate_pdb_growth([resp])
        transformed = transform_pdb_growth(validated)
        assert transformed[0].observation_date == date(2026, 9, 30)

    def test_reject_availability_not_available(self) -> None:
        resp = BpsVarResponse(var="104", year=2026, th_id=126, body={
            "status": "OK",
            "data-availability": "list-not-available",
            "tahun": [{"val": 126, "label": "2026"}],
            "datacontent": {},
        })
        with pytest.raises(ValueError, match="data-availability"):
            validate_pdb_growth([resp])


# --- TPT (var 543) ---

class TestTpt:
    def test_valid_annual_data(self) -> None:
        dc = {f"9999543{126:04d}189": "4.68"}
        resp = BpsVarResponse(var="543", year=2026, th_id=126, body={
            "status": "OK",
            "data-availability": "available",
            "tahun": [{"val": 126, "label": "2026"}],
            "datacontent": dc,
        })
        validated = validate_tpt([resp])
        assert len(validated) == 1
        transformed = transform_tpt(validated)
        assert len(transformed) == 1
        assert transformed[0].indicator_type == "tpt"
        assert transformed[0].value == Decimal("4.68")
        assert transformed[0].observation_date == date(2026, 12, 31)

    def test_average_semester_values(self) -> None:
        """2 semester values per year are averaged into one annual value."""
        validated = [(2024, 124, Decimal("4.82")), (2024, 124, Decimal("4.91"))]
        transformed = transform_tpt(validated)
        assert len(transformed) == 1
        # (4.82 + 4.91) / 2 = 4.865
        assert transformed[0].value == Decimal("4.865")

    def test_reject_availability_not_available(self) -> None:
        resp = BpsVarResponse(var="543", year=2026, th_id=126, body={
            "status": "OK",
            "data-availability": "list-not-available",
            "tahun": [{"val": 126, "label": "2026"}],
            "datacontent": {},
        })
        with pytest.raises(ValueError, match="data-availability"):
            validate_tpt([resp])


# --- Foreign reserves (var 1091) ---

class TestForeignReserves:
    def test_valid_annual_data(self) -> None:
        dc = {f"61091{125:04d}0": "93884.69"}
        resp = BpsVarResponse(var="1091", year=2025, th_id=125, body={
            "status": "OK",
            "data-availability": "available",
            "tahun": [{"val": 125, "label": "2025"}],
            "datacontent": dc,
        })
        validated = validate_foreign_reserves([resp])
        assert len(validated) == 1
        transformed = transform_foreign_reserves(validated)
        assert len(transformed) == 1
        assert transformed[0].indicator_type == "foreign_reserves"
        assert transformed[0].value == Decimal("93884.69")
        assert transformed[0].observation_date == date(2025, 12, 31)

    def test_reject_availability_not_available(self) -> None:
        resp = BpsVarResponse(var="1091", year=2025, th_id=125, body={
            "status": "OK",
            "data-availability": "list-not-available",
            "tahun": [{"val": 125, "label": "2025"}],
            "datacontent": {},
        })
        with pytest.raises(ValueError, match="data-availability"):
            validate_foreign_reserves([resp])
