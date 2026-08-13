"""Tests for the BI (BI7DRR + JISDOR) pipeline (fetcher-independent logic).

Covers the mandatory minimum tests from RULES.md 2:
  1. Parsing REAL saved XLSX exports (fixtures saved from Sesi 15 research)
     produces the expected rows / dates / Decimal values.
  2. The XLSX validator REJECTS a file whose structure drifted from the
     verified layout (instead of emitting half-parsed wrong numbers).
  3. One explicit format test: "4.75 %" -> Decimal('4.75').

Fixtures are the actual .xlsx bytes received from the BI "Unduh" button during
Sesi 15: a 2016 BI7DRR export (9 RDG rows) and a full-range JISDOR export
(3198 business days, 2013-05-20 .. 2026-08-07).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.transformers.bi import MacroIndicatorRecord, transform
from pipeline.validators.bi import (
    BiRow,
    BiSpreadsheet,
    BiStructureError,
    validate_xlsx,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "bi"


def _load(fname: str) -> bytes:
    return (FIXTURE_DIR / fname).read_bytes()


class TestParseRealBi7drrSample:
    """2016 BI7DRR export: 9 RDG rows, '15 Desember 2016' + '4.75 %' formats."""

    @pytest.fixture(autouse=True)
    def _sheet(self) -> None:
        self.sheet = validate_xlsx(_load("bi7drr_2016_sample.xlsx"), "bi_7drr")

    def test_header_dan_jumlah_baris(self) -> None:
        assert self.sheet.header == ["NO", "Tanggal", "BI-7Day-RR"]
        assert len(self.sheet.rows) == 9

    def test_baris_awal_format_tanggal_id(self) -> None:
        assert self.sheet.rows[0].date_raw == "15 Desember 2016"
        assert self.sheet.rows[0].value_raw == "4.75 %"

    def test_transform_persen_ke_decimal_dan_tanggal(self) -> None:
        records = transform([self.sheet])
        assert len(records) == 9
        # transform sorts ascending by (indicator_type, observation_date).
        assert records[0].observation_date == date(2016, 4, 21)
        assert records[0].value == Decimal("5.50")
        assert records[-1].observation_date == date(2016, 12, 15)
        assert records[-1].value == Decimal("4.75")
        assert records[0].indicator_type == "bi_7drr"
        assert records[0].source == "BI"
        assert all(r.observation_date.year == 2016 for r in records)

    def test_transform_nilai_lain(self) -> None:
        records = {r.observation_date: r.value for r in transform([self.sheet])}
        assert records[date(2016, 9, 22)] == Decimal("5.00")
        assert records[date(2016, 4, 21)] == Decimal("5.50")


class TestParseRealJisdorSample:
    """Full JISDOR export: US serial dates ('8/7/2026') + integer Rupiah."""

    @pytest.fixture(autouse=True)
    def _sheet(self) -> None:
        self.sheet = validate_xlsx(_load("jisdor_full_sample.xlsx"), "usd_idr")

    def test_header_dan_jumlah_baris(self) -> None:
        assert self.sheet.header == ["NO", "Tanggal", "Kurs"]
        assert len(self.sheet.rows) == 3198
        assert self.sheet.rows[0].date_raw == "8/7/2026 12:00:00 AM"
        assert self.sheet.rows[0].value_raw == "17913"

    def test_transform_kurs_ke_decimal_dan_tanggal(self) -> None:
        records = transform([self.sheet])
        assert len(records) == 3198
        # transform sorts ascending; records[0] = earliest = 2013-05-20,
        # records[-1] = newest = 2026-08-07.
        assert records[0].observation_date == date(2013, 5, 20)
        assert records[0].value == Decimal("9760")
        assert records[-1].observation_date == date(2026, 8, 7)
        assert records[-1].value == Decimal("17913")
        assert records[0].indicator_type == "usd_idr"

    def test_transform_tanggal_us_tidak_terbalik(self) -> None:
        # "8/7/2026" is 7 August (M/D), not 8 July.
        records = transform([self.sheet])
        assert records[-1].observation_date == date(2026, 8, 7)


class TestPercentParsing:
    """Explicit format test for the "% with a leading space" quirk."""

    def _sheet(self, value_raw: str, date_raw: str = "15 Desember 2016") -> BiSpreadsheet:
        return BiSpreadsheet(
            indicator_type="bi_7drr",
            header=["NO", "Tanggal", "BI-7Day-RR"],
            rows=[BiRow(no="1", date_raw=date_raw, value_raw=value_raw)],
        )

    def test_persen_dengan_spasi(self) -> None:
        assert transform([self._sheet("4.75 %")])[0].value == Decimal("4.75")

    def test_persen_tanpa_spasi(self) -> None:
        assert transform([self._sheet("5.5%")])[0].value == Decimal("5.5")

    def test_persen_desimal_koma(self) -> None:
        assert transform([self._sheet("6,25 %")])[0].value == Decimal("6.25")

    def test_nilai_bukan_persen_ditolak(self) -> None:
        with pytest.raises(ValueError, match="persen"):
            transform([self._sheet("4.75 USD")])


class TestValidatorRejectsStructureChange:
    def test_tolak_bukan_xlsx(self) -> None:
        with pytest.raises(BiStructureError, match="XLSX"):
            validate_xlsx(b"this is not a zip", "bi_7drr")

    def test_tolak_header_berubah(self) -> None:
        # Rebuild the real BI7DRR export with a renamed 3rd column.
        raw = _load("bi7drr_2016_sample.xlsx")
        z = zipfile.ZipFile(io.BytesIO(raw))
        parts = {n: z.read(n) for n in z.namelist()}
        # "BI-7Day-RR" -> "BI-RATE" to simulate an (old or changed) layout.
        parts["xl/sharedStrings.xml"] = parts["xl/sharedStrings.xml"].replace(
            b"BI-7Day-RR", b"BI-RATE"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
            for name, data in parts.items():
                out.writestr(name, data)
        with pytest.raises(BiStructureError, match="BERUBAH"):
            validate_xlsx(buf.getvalue(), "bi_7drr")

    def test_tolak_sheet_tanpa_header(self) -> None:
        raw = _load("bi7drr_2016_sample.xlsx")
        z = zipfile.ZipFile(io.BytesIO(raw))
        parts = {n: z.read(n) for n in z.namelist()}
        parts["xl/sharedStrings.xml"] = parts["xl/sharedStrings.xml"].replace(
            b"Tanggal", b"Periode"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
            for name, data in parts.items():
                out.writestr(name, data)
        with pytest.raises(BiStructureError, match="header"):
            validate_xlsx(buf.getvalue(), "bi_7drr")

    def test_tolak_indicator_tidak_dikenal(self) -> None:
        with pytest.raises(ValueError, match="tidak dikenal"):
            validate_xlsx(_load("bi7drr_2016_sample.xlsx"), "gdp_yoy")


class TestTransformerInputTypes:
    def test_transform_butuh_list_spreadsheet(self) -> None:
        with pytest.raises(Exception):
            transform("bukan list")  # type: ignore[arg-type]

    def test_macro_indicator_record_default_source(self) -> None:
        rec = MacroIndicatorRecord(indicator_type="usd_idr", observation_date=date(2026, 1, 2), value=Decimal("17000"))
        assert rec.source == "BI"