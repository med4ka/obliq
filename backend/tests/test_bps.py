"""Tests for the BPS IHK -> YoY pipeline (fetcher-independent logic).

Covers the two mandatory minimum tests from RULES.md 2:
  1. YoY transformation produces the value implied by the manual definition,
     using explicit sample IHK values.
  2. The Pydantic validator rejects malformed raw responses instead of passing
     them through to transform.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from pipeline.fetchers.bps import BpsVarResponse, fetch
from pipeline.transformers.bps import transform
from pipeline.validators.bps import (
    BpsMonthObservation,
    BpsYearData,
    BpsRawResponse,
    decode_datacontent_key,
    validate_years,
)


def _build_year(year: int, th_id: int, values: dict[int, str]) -> BpsYearData:
    return BpsYearData(
        year=year,
        th_id=th_id,
        observations=[
            BpsMonthObservation(th_id=th_id, month=m, value=Decimal(v))
            for m, v in sorted(values.items())
        ],
    )


class TestDecodeDatacontentKey:
    def test_januari_dan_desember(self) -> None:
        # key format: vervar(4) var(1709) th_id(04d) month (variable width)
        assert decode_datacontent_key("9999170901231", 123) == (123, 1)
        assert decode_datacontent_key("99991709012312", 123) == (123, 12)

    def test_bulan_11_tidak_ambigu_dengan_th_id(self) -> None:
        # "999917090123111" = vervar 9999 + var 1709 + th 0123 + month 111?? no:
        # real key for month 11 is var(1709)+th(0123)+month(11) -> "0...123111"
        assert decode_datacontent_key("99991709012311", 123) == (123, 11)
        # month=1 is single digit: "0123" + "1"
        assert decode_datacontent_key("9999170901231", 123) == (123, 1)


class TestYoyTransform:
    def test_yoy_hlm_dari_ihk_setahun_lalu(self) -> None:
        # IHK Jan - Jan last year. Pick easy-to-check values.
        # YoY(2022-01) = (120 - 100) / 100 * 100 = +20.0%
        data = [
            _build_year(2022, 122, {1: "120.00"}),
            _build_year(2021, 121, {1: "100.00"}),
        ]
        results = transform(data)
        assert len(results) == 1
        assert results[0].observation_date == date(2022, 1, 31)
        assert results[0].value == Decimal("20.0")

    def test_yoy_definisi_umum(self) -> None:
        # YoY = (IHK_now - IHK_12mo_ago) / IHK_12mo_ago * 100
        # (121 - 110) / 110 * 100 = 10.00 exactly
        data = [
            _build_year(2023, 123, {6: "121.00"}),
            _build_year(2022, 122, {6: "110.00"}),
        ]
        results = transform(data)
        assert len(results) == 1
        assert results[0].value == Decimal("10.0")

    def test_titik_tanpa_pasangan_setahun_lalu_skip(self) -> None:
        # 2022 without 2021 data -> all 2022 points skipped (not interpolated), with log (not silent).
        data = [_build_year(2022, 122, {1: "120.00", 2: "121.00"})]
        results = transform(data)
        assert results == []


class TestValidatorRejectsMalformed:
    @staticmethod
    def _raw(
        *,
        status: str = "OK",
        availability: str = "available",
        datacontent: dict[str, str] | None = None,
        tahun: list[dict] | None = None,
    ) -> dict:
        return {
            "status": status,
            "data-availability": availability,
            "last_update": "2023-12-01 08:22:44",
            "tahun": tahun if tahun is not None else [{"val": 123, "label": "2023"}],
            "datacontent": datacontent or {},
        }

    def test_tolak_respons_bukan_dict(self) -> None:
        with pytest.raises(TypeError):
            validate_years([["bukan", "object"]])

    def test_tolak_availability_tidak_available(self) -> None:
        raw = self._raw(availability="list-not-available")
        with pytest.raises(ValueError, match="data-availability"):
            validate_years([raw])

    def test_tolak_key_datacontent_tidak_dikenali(self) -> None:
        raw = self._raw(datacontent={"asdf": "135.87"})
        with pytest.raises(ValueError, match="tidak dikenali"):
            validate_years([raw])

    def test_tolak_nilai_non_numerik(self) -> None:
        raw = self._raw(datacontent={"9999170901231": "abc"})
        with pytest.raises(ValueError, match="non-numerik"):
            validate_years([raw])

    def test_tolak_status_tidak_ok(self) -> None:
        raw = self._raw(status="ERROR")
        with pytest.raises(ValidationError):
            BpsRawResponse.model_validate(raw)


class TestFetchYearSelection:
    """fetch(years=...) must honor a small range and skip unsupported years."""

    @staticmethod
    def _stub_response(year: int, th_id: int) -> BpsVarResponse:
        return BpsVarResponse(var="1709", year=year, th_id=th_id, body={"datacontent": {}})

    def test_select_subset_tahun(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("pipeline.fetchers.bps._get_api_key", lambda: "k")
        calls: list[tuple[int, int]] = []

        def fake_fetch(api_key: str, year: int, th_id: int) -> BpsVarResponse:
            calls.append((year, th_id))
            return self._stub_response(year, th_id)

        monkeypatch.setattr("pipeline.fetchers.bps._fetch_year", fake_fetch)

        result = fetch(years=[2022, 2023])
        assert [r.year for r in result] == [2022, 2023]
        assert calls == [(2022, 122), (2023, 123)]

    def test_skip_tahun_tidak_didukung(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("pipeline.fetchers.bps._get_api_key", lambda: "k")
        calls: list[int] = []

        def fake_fetch(api_key: str, year: int, th_id: int) -> BpsVarResponse:
            calls.append(year)
            return self._stub_response(year, th_id)

        monkeypatch.setattr("pipeline.fetchers.bps._fetch_year", fake_fetch)

        result = fetch(years=[2019, 2021, 2024])
        assert [r.year for r in result] == [2021]

    def test_default_kembali_semua_tahun(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("pipeline.fetchers.bps._get_api_key", lambda: "k")
        years: list[int] = []

        def fake_fetch(api_key: str, year: int, th_id: int) -> BpsVarResponse:
            years.append(year)
            return self._stub_response(year, th_id)

        monkeypatch.setattr("pipeline.fetchers.bps._fetch_year", fake_fetch)

        result = fetch()  # tahun kosong -> semua tahun yang diserve
        assert [r.year for r in result] == [2020, 2021, 2022, 2023]
        assert set(years) == {2020, 2021, 2022, 2023}