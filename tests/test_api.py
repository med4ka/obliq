"""API layer tests (read-only endpoints against the local database).

These are integration-ish: they exercise the real FastAPI app + real DB (the
Fase 0/1 seed + DJPPR/BI/BPS rows already present). Tests skip cleanly when
the database is unreachable so the pipeline unit-test suite still passes on a
machine without Postgres running.

Key assertions beyond happy-path shape:
  - money/rate Decimals serialize to exact STRINGS, never floats (SYSTEM.md 1.5);
  - dummy rows are honesty-tagged with is_dummy + the RULES.md 3 badge text;
  - empty-data responses are explicit (status="empty" + message), distinct from
    a 4xx client error and a 500 internal error.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.main import app
from db.connection import get_engine


def _db_reachable() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(), reason="database tidak reachable (tests API butuh DB lokal)"
)

client = TestClient(app)


class TestHealth:
    def test_health_ok(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "obliq-api"
        assert body["database"] == "ok"


class TestYieldCurveCurrent:
    def test_returns_points_with_audit_and_string_decimals(self) -> None:
        resp = client.get("/api/yield-curve/current")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["count"] > 0
        assert body["as_of"]  # latest observation_date across the curve

        for item in body["items"]:
            assert sorted(item) == sorted(
                [
                    "bond_code", "bond_name", "tenor_years", "coupon_rate",
                    "maturity_date", "observation_date", "yield_value",
                    "price", "source", "fetched_at", "is_estimated",
                ]
            )
            # Precision: yield is a string of exact digits, not a float.
            assert isinstance(item["yield_value"], str)
            # Audit trail (SYSTEM.md 1.2, SCHEMA.md).
            assert item["source"]  # DJPPR/BI/etc, non-empty
            assert item["fetched_at"]
            assert item["observation_date"]

    def test_sorted_by_tenor_ascending(self) -> None:
        body = client.get("/api/yield-curve/current").json()
        tenors = [it["tenor_years"] for it in body["items"]]
        # SPN (short tenor) first; tenor_years may be None for zero-coupon rows
        # stored without tenor -- nulls settle at the front via nullslast.
        non_null = [t for t in tenors if t is not None]
        parsed = [float(t) for t in non_null]
        assert parsed == sorted(parsed)


class TestYieldCurveHistory:
    def test_history_for_existing_bond(self) -> None:
        # Take a real code straight from the DB through the app itself is not
        # possible in a test; use a bond we know exists from the DJPPR backfill.
        resp = client.get("/api/yield-curve/history", params={"bond_code": "FR0100"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["bond_code"] == "FR0100"
        assert body["count"] > 0
        dates = [it["observation_date"] for it in body["items"]]
        assert dates == sorted(dates)
        for it in body["items"]:
            assert isinstance(it["yield_value"], str)
            assert it["source"]
            assert it["fetched_at"]

    def test_history_ranged_and_empty_response_is_explicit(self) -> None:
        # Range with no data -> 200 + status "empty" + message (not silent []).
        resp = client.get(
            "/api/yield-curve/history",
            params={"bond_code": "FR0100", "start": "2020-01-01", "end": "2020-12-31"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "empty"
        assert body["count"] == 0
        assert body["items"] == []
        assert "Tidak ada observasi" in body["message"]

    def test_unknown_bond_is_not_found(self) -> None:
        resp = client.get("/api/yield-curve/history", params={"bond_code": "NOT-A-BOND"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_found"
        assert "tidak ditemukan" in body["message"]

    def test_invalid_range_is_client_error(self) -> None:
        resp = client.get(
            "/api/yield-curve/history",
            params={"bond_code": "FR0100", "start": "2026-08-01", "end": "2020-01-01"},
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]


class TestMacroHistory:
    def test_history_existing_indicator(self) -> None:
        resp = client.get("/api/macro/inflation_yoy")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["indicator_type"] == "inflation_yoy"
        assert body["count"] > 0
        for it in body["items"]:
            assert isinstance(it["value"], str)
            assert it["source"]
            assert it["fetched_at"]
            assert it["observation_date"]
            assert "is_dummy" in it
            assert "notice" in it

    def test_dummy_rows_carry_honesty_signal(self) -> None:
        # DUMMY_CONTOH rows are inflation_yoy in 2026; BPS is only up to 2023.
        resp = client.get(
            "/api/macro/inflation_yoy", params={"start": "2026-01-01", "end": "2026-12-31"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] > 0
        dummy = [it for it in body["items"] if it["is_dummy"]]
        assert dummy, "expected dummy seed rows inside 2026 to be flagged"
        for it in dummy:
            assert it["source"].startswith("DUMMY")
            assert it["notice"]  # badge text present, per RULES.md 3

    def test_empty_history_explicit(self) -> None:
        resp = client.get(
            "/api/macro/usd_idr", params={"start": "2030-01-01", "end": "2030-12-31"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "empty"
        assert body["count"] == 0
        assert "Tidak ada data" in body["message"]

    def test_invalid_range_is_client_error(self) -> None:
        resp = client.get(
            "/api/macro/usd_idr", params={"start": "2026-08-01", "end": "2020-01-01"}
        )
        assert resp.status_code == 422


class TestMacroLatest:
    def test_snapshot_all_indicators(self) -> None:
        resp = client.get("/api/macro/latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["count"] >= 3  # inflation_yoy, bi_7drr, usd_idr
        types = {it["indicator_type"] for it in body["items"]}
        assert {"inflation_yoy", "bi_7drr", "usd_idr"} <= types
        for it in body["items"]:
            assert isinstance(it["value"], str)
            assert it["source"]
            assert it["fetched_at"]
            assert it["observation_date"]
            assert "is_dummy" in it

    def test_latest_includes_dummy_flag_for_seed(self) -> None:
        # Latest inflation_yoy row is a DUMMY_CONTOH 2026 row (BPS stops 2023).
        body = client.get("/api/macro/latest").json()
        infl = next(it for it in body["items"] if it["indicator_type"] == "inflation_yoy")
        assert infl["is_dummy"] is True
        assert infl["notice"]


class TestDecimalPrecisionUnit:
    """Layer checks for the Decimal -> string guarantee, independent of DB state."""

    def test_json_has_string_not_float_for_decimal(self) -> None:
        from api.schemas import MacroItem, YieldCurvePoint
        from datetime import date, datetime
        from decimal import Decimal

        m = MacroItem(
            indicator_type="usd_idr",
            observation_date=date(2026, 8, 7),
            value=Decimal("17913.0000"),
            source="BI",
            fetched_at=datetime(2026, 8, 10),
            is_dummy=False,
        )
        raw = m.model_dump_json()
        assert '"17913.0000"' in raw

        p = YieldCurvePoint(
            bond_code="FR0100",
            bond_name="X",
            tenor_years=Decimal("10.00"),
            coupon_rate=Decimal("6.375"),
            maturity_date=date(2036, 8, 15),
            observation_date=date(2026, 8, 4),
            yield_value=Decimal("7.2957"),
            price=None,
            source="DJPPR",
            fetched_at=datetime(2026, 8, 10),
            is_estimated=False,
        )
        raw_p = p.model_dump_json()
        assert '"7.2957"' in raw_p
        # No Float coercion anywhere in the JSON layer.
        assert "7.29570000000000" not in raw_p  # 147e-... float repr would differ