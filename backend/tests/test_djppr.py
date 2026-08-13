"""Tests for the DJPPR auction pipeline (fetcher-independent logic).

Covers the mandatory minimum tests from RULES.md 2:
  1. Parsing a REAL saved @Konten HTML sample produces the expected series /
     yields / coupons / maturities (fixtures saved from Sesi 7 research).
  2. The validator REJECTS a table whose column structure drifted from the
     verified layout (instead of emitting half-parsed wrong numbers).

The @Konten fixtures are the actual HTML pulled from djppr pages on 2026-08-04
and 2023-12-12; the 2023 one exercises the row-order variation (extra rows like
"Yield tertinggi/terendah", "Nominal kompetitif") to prove the label-keyed
parser is order-independent.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from pipeline.fetchers.djppr import DjpprPage, _parse_slug_date
from pipeline.transformers.djppr import transform
from pipeline.validators.djppr import (
    DjpprAuction,
    DjpprNoAwardError,
    DjpprStructureError,
    normalize_label,
    validate_pages,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "djppr"


def _wrap_konten(html: str, auction_date: str) -> DjpprPage:
    """Build a minimal DjpprPage whose widget tree holds the @Konten HTML."""
    tree = [
        {
            "widgetType": "section",
            "rows": [
                {
                    "cols": [
                        {
                            "modules": [
                                {
                                    "widgetType": "repeater",
                                    "data": [
                                        {
                                            "@Konten": html,
                                            "@Tanggal": auction_date,
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ],
        }
    ]
    return DjpprPage(
        page_id=1,
        url_path="hasillelangsuratutangnegarapadahariselasa,tanggal",
        title="Hasil Lelang Surat Utang Negara",
        content_tree=tree,
        fetched_at=datetime.now(),
    )


class TestParseRealSample2026:
    """Parse the 2026-08-04 fixture: 9 series, including SPN + FR."""

    @pytest.fixture(autouse=True)
    def _auction(self) -> None:
        html = (FIXTURE_DIR / "konten_2026_08_04_0.html").read_text(encoding="utf-8")
        page = _wrap_konten(html, "4 Agustus 2026")
        self.auction: DjpprAuction = validate_pages([page])[0]

    def test_series_count_dan_auction_date(self) -> None:
        assert len(self.auction.series) == 9
        assert self.auction.auction_date.isoformat() == "2026-08-04"
        assert self.auction.settlement_date.isoformat() == "2026-08-06"

    def test_spn_zero_coupon_yield_dan_maturity(self) -> None:
        spn = next(s for s in self.auction.series if s.code == "SPN01260905")
        assert spn.weighted_yield == Decimal("6.89000")
        assert spn.coupon_rate is None  # "Diskonto"
        assert spn.maturity_date.isoformat() == "2026-09-05"
        assert spn.bid_to_cover == Decimal("2.21")

    def test_fr_coupon_yield(self) -> None:
        fr0110 = next(s for s in self.auction.series if s.code == "FR0110")
        assert fr0110.weighted_yield == Decimal("7.29574")
        assert fr0110.coupon_rate == Decimal("7.25000")
        assert fr0110.maturity_date.isoformat() == "2032-05-15"


class TestParseRealSample2023:
    """2023-12-12 fixture has a different row set/order; parser must cope."""

    @pytest.fixture(autouse=True)
    def _auction(self) -> None:
        html = (FIXTURE_DIR / "konten_2023_12_12_0.html").read_text(encoding="utf-8")
        page = _wrap_konten(html, "12 Desember 2023")
        self.auction: DjpprAuction = validate_pages([page])[0]

    def test_series_count(self) -> None:
        assert len(self.auction.series) == 7
        codes = [s.code for s in self.auction.series]
        assert codes == ["SPN03240313", "SPN12241212", "FR0101", "FR0100", "FR0098", "FR0097", "FR0089"]

    def test_weighted_yield_kunci(self) -> None:
        by_code = {s.code: s for s in self.auction.series}
        assert by_code["FR0101"].weighted_yield == Decimal("6.70988")
        assert by_code["FR0101"].coupon_rate == Decimal("6.87500")
        assert by_code["FR0089"].maturity_date.isoformat() == "2051-08-15"
        assert by_code["SPN03240313"].coupon_rate is None

    def test_bid_to_cover(self) -> None:
        by_code = {s.code: s for s in self.auction.series}
        assert by_code["FR0101"].bid_to_cover == Decimal("1.92")


class TestValidatorRejectsStructureChange:
    def _fixture_html(self) -> str:
        return (FIXTURE_DIR / "konten_2026_08_04_0.html").read_text(encoding="utf-8")

    def test_tolak_tabel_tanpa_baris_yield(self) -> None:
        # Drop the whole weighted-yield row -> the decisive results table
        # no longer exists, so the validator must raise.
        html = re.sub(
            r"<tr>[\s\S]*?rata-rata tertimbang yang dimenangkan[\s\S]*?</tr>",
            "",
            self._fixture_html(),
        )
        assert "tertimbang yang dimenangkan" not in html
        page = _wrap_konten(html, "4 Agustus 2026")
        with pytest.raises(DjpprStructureError, match="Yield rata-rata tertimbang"):
            validate_pages([page])

    def test_tolak_jumlah_nilai_tidak_cocok_seri(self) -> None:
        # Remove one series value cell from the coupon row -> value count no
        # longer matches the series-code count; validator must raise.
        html = self._fixture_html()
        idx = html.find("Tingkat kupon")
        row_start = html.rfind("<tr", 0, idx)
        row_end = html.find("</tr>", idx) + len("</tr>")
        row = html[row_start:row_end]
        # Cells span multiple lines (<td>\n<p>value</p>\n</td>); use DOTALL.
        m = re.search(r"<td[^>]*>\s*(<p[^>]*>)", row)  # first cell (label)
        assert m is not None, "coupon row must have a label cell"
        rest = row[m.end():]
        m2 = re.search(r"<td>.*?</td>", rest, re.S)
        assert m2 is not None, "coupon row should have a first value <td>"
        mutated_row = row[: m.end() + m2.start()] + row[m.end() + m2.end():]
        html = html[:row_start] + mutated_row + html[row_end:]
        page = _wrap_konten(html, "4 Agustus 2026")
        with pytest.raises(DjpprStructureError, match="tingkat kupon"):
            validate_pages([page])

    def test_tolak_tanpa_kode_seri(self) -> None:
        html = self._fixture_html().replace("SPN01260905", "BUKAN_SERI")
        page = _wrap_konten(html, "4 Agustus 2026")
        with pytest.raises(DjpprStructureError, match="kode seri"):
            validate_pages([page])


class TestParseNotAwardedSeries:
    """2026-07-21 fixture: SPN01260822 was offered but NOT awarded ("-")."""

    @pytest.fixture(autouse=True)
    def _auction(self) -> None:
        html = (FIXTURE_DIR / "konten_2026_07_21_0.html").read_text(encoding="utf-8")
        page = _wrap_konten(html, "21 Juli 2026")
        self.auction: DjpprAuction = validate_pages([page])[0]

    def test_seri_tidak_dimenangkan_yield_none(self) -> None:
        spn = next(s for s in self.auction.series if s.code == "SPN01260822")
        assert spn.weighted_yield is None
        assert spn.bid_to_cover is None

    def test_seri_dimenangkan_yield_terisi(self) -> None:
        by_code = {s.code: s for s in self.auction.series}
        assert by_code["FR0108"].weighted_yield == Decimal("7.28973")

    def test_series_count_termasuk_yang_none(self) -> None:
        # The series is still present as an offered instrument, just unawarded.
        assert len(self.auction.series) == 9


class TestTransformer:
    def _auction(self) -> DjpprAuction:
        html = (FIXTURE_DIR / "konten_2026_08_04_0.html").read_text(encoding="utf-8")
        return validate_pages([_wrap_konten(html, "4 Agustus 2026")])[0]

    def test_transform_satu_lelang_banyak_seri(self) -> None:
        auction = self._auction()
        out = transform([auction])
        assert len(out["bonds"]) == 9  # one bond per distinct series code
        assert len(out["yield_obs"]) == 9  # 1 row per (series, auction date)
        fr = next(b for b in out["bonds"] if b.code == "FR0110")
        assert fr.type == "government"
        assert fr.coupon_rate == Decimal("7.25000")
        assert fr.maturity_date.isoformat() == "2032-05-15"
        assert fr.tenor_years == Decimal("5.78")  # (2032-05-15 - 2026-08-04)/365.25

    def test_transform_seri_yang_sama_di_dua_lelang(self) -> None:
        auction = self._auction()
        # Re-auctioning the same code on a second date -> 1 bond, 2 observations.
        out = transform([auction, auction])
        assert len(out["bonds"]) == 9
        assert len(out["yield_obs"]) == 18
        codes = {b.code for b in out["bonds"]}
        assert codes == {s.code for s in auction.series}

    def test_transform_spn_coupon_none(self) -> None:
        auction = self._auction()
        out = transform([auction])
        spn = next(b for b in out["bonds"] if b.code == "SPN01260905")
        assert spn.coupon_rate is None

    def test_transform_seri_tidak_dimenangkan_tanpa_observasi(self) -> None:
        html = (FIXTURE_DIR / "konten_2026_07_21_0.html").read_text(encoding="utf-8")
        auction = validate_pages([_wrap_konten(html, "21 Juli 2026")])[0]
        out = transform([auction])
        # only the 8 awarded series become bonds + observations
        assert len(out["bonds"]) == 8
        assert len(out["yield_obs"]) == 8
        codes = {b.code for b in out["bonds"]}
        assert "SPN01260822" not in codes
        for obs in out["yield_obs"]:
            assert obs.bond_code != "SPN01260822"


class TestSlugAuctionDate:
    """The listing date filter keys on the slug-embedded auction date.

    Legacy pages carry the CMS migration date in DPublishedID, so the auction
    date must come from the UrlPath slug ("tanggal27april2021"). These slugs
    are the real rows observed in the DJPPR listing.
    """

    def test_regular_slug(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegarapadahariselasa,tanggal27april2021"
        ).isoformat() == "2021-04-27"

    def test_greenshoe_slug(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegaratambahan(greenshoeoption)padaharirabu,14april2021"
        ).isoformat() == "2021-04-14"

    def test_legacy_2019_slug(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegarapadahariselasatanggal7mei2019"
        ).isoformat() == "2019-05-07"

    def test_modern_2026_slug(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegarapadahariselasa,tanggal4agustus2026"
        ).isoformat() == "2026-08-04"

    def test_old_spelling_nopember(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegarapadahariselasatanggal8nopember2016"
        ).isoformat() == "2016-11-08"

    def test_slug_tanpa_tanggal(self) -> None:
        assert _parse_slug_date(
            "hasillelangsuratutangnegaraspn12160708(reopening),fr0053(reopening),fr0056"
        ) is None


class TestParseLegacyQuirks2021:
    """2021 pages introduced two layout quirks the 2023/2026 fixtures lack:

    1. Greenshoe codes split across tags: "<strong>FR00</strong><strong>86</strong>"
       -> "FR0086" (code normalization).
    2. The old official spelling "Nopember" for November in maturity dates.
    These are the ONLY structure deltas approved for parsing (Sesi 9); anything
    else must still raise DjpprStructureError.
    """

    def _parse(self, fname: str, auction_date: str) -> DjpprAuction:
        html = (FIXTURE_DIR / fname).read_text(encoding="utf-8")
        return validate_pages([_wrap_konten(html, auction_date)])[0]

    def test_greenshoe_kode_terbelah_di_merge(self) -> None:
        auction = self._parse("konten_2021_04_14_greenshoe_0.html", "14 April 2021")
        codes = [s.code for s in auction.series]
        assert codes == ["FR0086", "FR0087", "FR0088", "FR0083", "FR0089"]
        assert auction.auction_date.isoformat() == "2021-04-14"
        assert auction.settlement_date.isoformat() == "2021-04-15"

    def test_greenshoe_yield_kupon_maturity(self) -> None:
        auction = self._parse("konten_2021_04_14_greenshoe_0.html", "14 April 2021")
        by_code = {s.code: s for s in auction.series}
        assert by_code["FR0086"].weighted_yield == Decimal("5.74944")
        assert by_code["FR0086"].coupon_rate == Decimal("5.50000")
        assert by_code["FR0089"].weighted_yield == Decimal("7.08745")
        assert by_code["FR0089"].maturity_date.isoformat() == "2051-08-15"
        assert by_code["FR0083"].maturity_date.isoformat() == "2040-04-15"

    def test_greenshoe_label_kupon_pendek_parsed(self) -> None:
        # The 2021 greenshoe table labels the coupon row just "Kupon" (not
        # "Tingkat kupon"). This alias must resolve; otherwise the row would be
        # reported missing and the whole page rejected.
        auction = self._parse("konten_2021_04_14_greenshoe_0.html", "14 April 2021")
        coupons = {s.code: s.coupon_rate for s in auction.series}
        assert coupons == {
            "FR0086": Decimal("5.50000"),
            "FR0087": Decimal("6.50000"),
            "FR0088": Decimal("6.25000"),
            "FR0083": Decimal("7.50000"),
            "FR0089": Decimal("6.87500"),
        }

    def test_nopember_spelling_18_agustus(self) -> None:
        auction = self._parse("konten_2021_08_18_0.html", "18 Agustus 2021")
        by_code = {s.code: s for s in auction.series}
        assert "SPN03211118" in by_code
        assert by_code["SPN03211118"].maturity_date.isoformat() == "2021-11-18"  # "18 Nopember 2021"
        assert by_code["SPN03211118"].coupon_rate is None  # Diskonto
        assert by_code["SPN03211118"].weighted_yield == Decimal("2.81760")
        assert by_code["FR0090"].weighted_yield == Decimal("5.27720")
        assert len(auction.series) == 7

    def test_nopember_spelling_3_agustus(self) -> None:
        auction = self._parse("konten_2021_08_03_0.html", "3 Agustus 2021")
        by_code = {s.code: s for s in auction.series}
        assert by_code["SPN12211104"].maturity_date.isoformat() == "2021-11-04"  # "4 Nopember 2021"
        assert by_code["SPN12211104"].weighted_yield == Decimal("2.82150")
        assert by_code["FR0091"].weighted_yield == Decimal("6.27853")
        assert len(auction.series) == 7


class TestNoAwardSkip:
    """2018-05-08 (PageId 3146): auction CANCELLED -- government accepted no bids.

    The page holds only the bid-summary table, so there is genuinely no results
    table / weighted-yield row. This is a DATA state (approved: documented
    skip), not the structural drift that must raise plain DjpprStructureError.
    """

    def _page(self) -> DjpprPage:
        html = (FIXTURE_DIR / "konten_2018_05_08_noaward.html").read_text(encoding="utf-8")
        return _wrap_konten(html, "8 Mei 2018")

    def test_no_award_menimbulkan_error_khusus(self) -> None:
        with pytest.raises(DjpprNoAwardError, match="tidak menerima semua penawaran"):
            validate_pages([self._page()])

    def test_no_award_adalah_juga_structure_error(self) -> None:
        # Broad DjpprStructureError catch-alls (e.g. runner) must still see it.
        with pytest.raises(DjpprStructureError):
            validate_pages([self._page()])

    def test_no_award_bukan_halaman_normal(self) -> None:
        # A normal awarded auction must NOT trip the no-award guard.
        html = (FIXTURE_DIR / "konten_2026_08_04_0.html").read_text(encoding="utf-8")
        auction = validate_pages([_wrap_konten(html, "4 Agustus 2026")])[0]
        assert len(auction.series) == 9


class TestLabelNormalization:
    def test_huruf_besar_tanda_baca(self) -> None:
        assert normalize_label("Bid-to-cover-ratio") == "bid to cover ratio"
        assert normalize_label("  Yield rata-rata\ntertimbang ") == "yield rata rata tertimbang"
        assert normalize_label("Tingkat kupon") == "tingkat kupon"