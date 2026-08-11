"""Pydantic validation of DJPPR auction-result pages.

WHAT is validated: the auction page content tree (widget JSON) whose repeater
`@Konten` field holds an HTML <table> with one column per SUN series auctioned
that day. This module parses that table with BeautifulSoup, VERIFIES the
expected rows exist (series codes + weighted-average-yield row + coupon row +
maturity row), and only then maps values into a Pydantic schema.

WHY fail loudly instead of guessing: government pages have changed layout
without notice before (RULES.md 1). If a row we depend on is missing, or a
series-code/value count does not line up, we RAISE a DjpprStructureError in
stead of emitting half-parsed numbers that would silently corrupt the
yield curve. Sesi 7 verified this exact structure on 2023 and 2026 pages;
any drift away from it is a real change that must be inspected manually.

Number formats handled (RULES.md 4: government data quirks):
  - percentages arrive as "7,29574%" (comma = decimal separator, EN unit)
  - coupons arrive as "7,25000%" or "Diskonto" (SPN zero-coupon notes)
  - dates arrive as "15 Mei 2032" (Indonesian month names)
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# SUN series codes look like "FR0110" (fixed-rate) or "SPN01260905" (T-bills).
_CODE_RE = re.compile(r"^[A-Z]{2,6}\d{2,8}$")
# Legacy pages split a code across adjacent tags ("<strong>FR00</strong><strong>86</strong>"),
# which BeautifulSoup get_text(" ") renders as "FR00 86". Codes must be joined
# back together before regex matching / storage (RULES.md 4).
_CODE_JOIN_RE = re.compile(r"\s+")
# We only care about the decisive results table. Label matching is done on a
# normalized form (lowercase + collapse + drop non-alphanumeric hyphens etc).
_LABEL_NORM_RE = re.compile(r"[^a-z0-9 ]+")

_LABEL_WEIGHTED_YIELD = "yield rata rata tertimbang yang dimenangkan"
_LABEL_COUPON = "tingkat kupon"
# 2021 greenshoe pages label the coupon row just "Kupon" (approved Sesi 10
# alias); everything else uses "Tingkat kupon".
_LABEL_COUPON_ALIASES = (_LABEL_COUPON, "kupon")
_LABEL_MATURITY = "tanggal jatuh tempo"
_LABEL_BID_TO_COVER = "bid to cover ratio"
_LABEL_SETTLEMENT = "tanggal setelmen penerbitan"

_ID_MONTHS = {
    "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
    "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
    "September": 9, "Oktober": 10, "November": 11, "Nopember": 11, "Desember": 12,
}

# A cancelled auction: the government accepts NO bids, so the page holds only
# the bid-summary table and no results table. Phrase variants guard against
# minor rewording between releases (observed exact wording on 2018-05-08).
_NO_AWARD_RE = re.compile(
    r"tidak menerima\s+semua\s+penawaran|menolak\s+(?:semua|seluruh)\s+penawaran",
    re.IGNORECASE,
)


class DjpprStructureError(ValueError):
    """The auction HTML/table does not match the verified DJPPR layout.

    Raised instead of parsing wrong numbers silently (RULES.md 1 / SYSTEM.md 3).
    """


class DjpprNoAwardError(DjpprStructureError):
    """The auction page declares the government accepted NO bids at all.

    A cancelled auction (government rejects every submitted bid) is a DATA
    state, not a layout drift: there is genuinely no results table because
    nothing was won (observed 2018-05-08, PageId 3146). The runner treats it
    as a documented skip (logged), not as a DjpprStructureError that demands
    manual re-inspection. Subclassing DjpprStructureError keeps any broad
    catch-all from silently swallowing it.
    """


def normalize_label(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation for label matching."""
    lowered = text.lower()
    lowered = _LABEL_NORM_RE.sub(" ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def normalize_code(value: str) -> str:
    """Remove any whitespace a legacy layout split across tags.

    "FR00 86" -> "FR0086". Makes the stored bond code match the official
    series code and lets [A-Z]{2,6}\\d{2,8} match again.
    """
    return _CODE_JOIN_RE.sub("", value).strip()


def _is_no_award(konten: str) -> bool:
    """True if the page declares the auction's bids were ALL rejected."""
    return _NO_AWARD_RE.search(konten) is not None


def _parse_percent(value: str) -> Decimal:
    """'7,29574%' -> Decimal('7.29574'). Comma is the decimal separator."""
    cleaned = value.strip().replace("%", "").replace(",", ".").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Nilai persen tidak valid: {value!r}") from exc


def _parse_percent_or_none(value: str) -> Decimal | None:
    """Parse a percent, returning None for a not-awarded series ("-").

    DJPPR marks a series that received no winning bids with "-" in the yield /
    bid-to-cover / nominal rows. That is a DATA quirk (not a structure change):
    the column exists and the row is intact, the value simply says "not
    awarded". Returning None lets the transformer skip the observation while
    still recording the bond metadata.
    """
    stripped = value.strip()
    if stripped in ("-", "–", "—", ""):
        return None
    return _parse_percent(stripped)


def _parse_id_date(value: str) -> date:
    """'15 Mei 2032' -> date(2032, 5, 15)."""
    parts = value.strip().split()
    if len(parts) != 3 or not parts[0].isdigit() or not parts[2].isdigit():
        raise ValueError(f"Tanggal tidak valid: {value!r}")
    month = _ID_MONTHS.get(parts[1])
    if month is None:
        raise ValueError(f"Nama bulan tidak dikenal: {parts[1]!r}")
    try:
        return date(int(parts[2]), month, int(parts[0]))
    except ValueError as exc:
        raise ValueError(f"Tanggal di luar rentang kalender: {value!r}") from exc


class DjpprSeries(BaseModel):
    """One series (one column) parsed from a single auction table."""

    code: str = Field(min_length=3)
    weighted_yield: Decimal | None  # None = series not awarded ("-" in DJPPR)
    coupon_rate: Decimal | None  # None = zero-coupon ("Diskonto") or not awarded
    maturity_date: date
    bid_to_cover: Decimal | None = None

    @field_validator("code")
    @classmethod
    def _code_must_look_like_sun_series(cls, v: str) -> str:
        if not _CODE_RE.match(v):
            raise ValueError(f"Kode seri tidak seperti seri SUN: {v!r}")
        return v


class DjpprAuction(BaseModel):
    """Validated result of ONE auction page."""

    page_id: int
    url_path: str
    title: str
    auction_date: date  # THE auction date, used as observation_date
    settlement_date: date | None
    series: list[DjpprSeries]


def _walk_objects(obj: Any):
    """Yield every dict in a nested structure (widget tree)."""
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_objects(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_objects(item)


def _find_konten_and_auction_date(content_tree: Any) -> tuple[str | None, date | None]:
    """Find (@Konten html, @Tanggal auctionDate) in the repeater data rows.

    Some pages may have multiple repeaters/rows; we take the first non-empty
    @Konten and the row-level @Tanggal if present.
    """
    konten: str | None = None
    tanggal_raw: str | None = None
    for node in _walk_objects(content_tree):
        if isinstance(node, dict):
            row_konten = node.get("@Konten") or node.get("@content")
            if isinstance(row_konten, str) and "<table" in row_konten and konten is None:
                konten = row_konten
            row_tanggal = node.get("@Tanggal") or node.get("@tanggal")
            if isinstance(row_tanggal, str) and tanggal_raw is None:
                tanggal_raw = row_tanggal
    auction_date: date | None = None
    if tanggal_raw:
        try:
            auction_date = _parse_id_date(tanggal_raw)
        except ValueError as exc:
            logger.warning("Auction date @Tanggal tidak bisa diparse %r: %s", tanggal_raw, exc)
    return konten, auction_date


def _table_rows(table: BeautifulSoup) -> list[list[str]]:
    """Return table rows as lists of raw cell texts.

    Only the LABEL cell (index 0) is normalized for matching; value cells keep
    their raw text ("7,29574%", "Diskonto", "15 Mei 2032") because
    normalize_label would strip the digits/comma the parsers rely on.
    """
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        rows.append(cells)
    return rows


def _find_series_code_row(rows: list[list[str]]) -> int:
    """Index of the row holding the SUN series codes.

    The verified DJPPR layout: a header row starts with a "Keterangan" label
    cell, and the very next row is the series codes ("FR0110 SPN01260905 ...").
    Match that anchored pattern -- a bare ">=2 code-like cells" heuristic could
    false-positive on other tables.
    """
    for idx, cells in enumerate(rows[:-1]):
        if not cells:
            continue
        if normalize_label(cells[0]) != "keterangan":
            continue
        next_cells = rows[idx + 1]
        codes = [c for c in next_cells if c]
        if codes and all(_CODE_RE.match(normalize_code(c)) for c in codes):
            return idx + 1
    raise DjpprStructureError("Tidak ada baris kode seri (mis. FR0110/SPN...) di tabel hasil lelang")


def _find_table_with_yield_row(soup: BeautifulSoup) -> tuple[BeautifulSoup, list[list[str]]]:
    """Pick the table containing the decisive weighted-yield row.

    A page may embed several tables (penawaran summary + results). We only
    need the results table; it is the one with the weighted-average-yield label.
    """
    for table in soup.find_all("table"):
        rows = _table_rows(table)
        for cells in rows:
            if cells and normalize_label(cells[0]) == _LABEL_WEIGHTED_YIELD:
                return table, rows
    raise DjpprStructureError(
        "Tidak ada tabel hasil lelang: kolom 'Yield rata-rata tertimbang yang dimenangkan' tidak ditemukan"
    )


def _extract_row_by_label(rows: list[list[str]], label: str | tuple[str, ...]) -> list[str] | None:
    """Find the row whose normalized first cell equals `label` (or any alias)."""
    labels = (label,) if isinstance(label, str) else label
    for cells in rows:
        if cells and normalize_label(cells[0]) in labels:
            return cells
    return None


def _row_values(cells: list[str]) -> list[str]:
    """Cell values after the label; drop empties at the tail."""
    values = cells[1:]
    while values and not values[-1]:
        values.pop()
    return values


def _parse_table(
    rows: list[list[str]], n_series: int, *, page_id: int, url_path: str
) -> dict[str, list[str]]:
    """Validate + extract every expected row; raise on drift/discrepancy.

    Returns {field: [per-series raw value cell]} plus settlement handled by
    caller (it is a single colspan value shared by all series).
    """
    yield_row = _extract_row_by_label(rows, _LABEL_WEIGHTED_YIELD)
    coupon_row = _extract_row_by_label(rows, _LABEL_COUPON_ALIASES)
    maturity_row = _extract_row_by_label(rows, _LABEL_MATURITY)
    btc_row = _extract_row_by_label(rows, _LABEL_BID_TO_COVER)
    settlement_row = _extract_row_by_label(rows, _LABEL_SETTLEMENT)

    missing = [
        name
        for name, row in [
            ("yield rata-rata tertimbang yang dimenangkan", yield_row),
            ("tingkat kupon", coupon_row),
            ("tanggal jatuh tempo", maturity_row),
        ]
        if row is None
    ]
    if missing:
        raise DjpprStructureError(
            f"Struktur tabel hasil lelang BERUBAH (page_id={page_id} url={url_path}): "
            f"baris yang hilang: {', '.join(missing)}. Stop dan reviu manual."
        )

    def checked(r: list[str], what: str) -> list[str]:
        values = _row_values(r)
        if len(values) != n_series:
            raise DjpprStructureError(
                f"Struktur tabel hasil lelang BERUBAH (page_id={page_id} url={url_path}): "
                f"baris '{what}' punya {len(values)} nilai, padahal kode seri = {n_series}"
            )
        return values

    return {
        "weighted_yield": checked(yield_row, "yield rata-rata tertimbang yang dimenangkan"),
        "coupon": checked(coupon_row, "tingkat kupon"),
        "maturity": checked(maturity_row, "tanggal jatuh tempo"),
        "bid_to_cover": checked(btc_row, "bid-to-cover-ratio") if btc_row else [None] * n_series,
        "settlement": _row_values(settlement_row) if settlement_row else [],
    }


def validate_page(page: object) -> DjpprAuction:
    """Validate one fetched DJPPR page into a DjpprAuction (or raise)."""
    content_tree = getattr(page, "content_tree", None)
    url_path = getattr(page, "url_path", "")
    title = getattr(page, "title", "")
    page_id = int(getattr(page, "page_id", 0))

    if not isinstance(content_tree, list):
        raise DjpprStructureError(
            f"Halaman {url_path!r} tidak punya widget tree list (adu PageContentLive={type(content_tree).__name__})"
        )

    konten, auction_date = _find_konten_and_auction_date(content_tree)
    if not konten:
        raise DjpprStructureError(f"Halaman {url_path!r} tidak memuat @Konten berisi tabel lelang")

    if _is_no_award(konten):
        raise DjpprNoAwardError(
            f"Halaman {url_path!r} (page_id={page_id}): lelang DIBATALKAN -- "
            f"Pemerintah tidak menerima semua penawaran, tidak ada hasil lelang yang dicatat"
        )

    soup = BeautifulSoup(konten, "lxml")
    tables = soup.find_all("table")
    if not tables:
        raise DjpprStructureError(f"Halaman {url_path!r} tidak memuat <table> di @Konten")

    table, rows = _find_table_with_yield_row(soup)
    code_row_idx = _find_series_code_row(rows)
    codes = [normalize_code(c) for c in rows[code_row_idx] if c]
    if len(codes) < 1:
        raise DjpprStructureError(f"Halaman {url_path!r}: tidak ada kode seri")

    fields = _parse_table(rows, len(codes), page_id=page_id, url_path=url_path)

    settlement: date | None = None
    if fields["settlement"]:
        try:
            settlement = _parse_id_date(fields["settlement"][0])
        except ValueError as exc:
            raise DjpprStructureError(
                f"Halaman {url_path!r}: tanggal setelmen tidak valid ({fields['settlement'][0]!r}): {exc}"
            )

    if auction_date is None:
        raise DjpprStructureError(
            f"Halaman {url_path!r}: tanggal lelang (@Tanggal) tidak ditemukan / tidak bisa diparse"
        )

    series: list[DjpprSeries] = []
    for i, code in enumerate(codes):
        coupon_cell = fields["coupon"][i].strip().lower()
        if coupon_cell in ("diskonto", "-", "–", "—"):
            coupon = None
        else:
            try:
                coupon = _parse_percent(fields["coupon"][i])
            except ValueError as exc:
                raise DjpprStructureError(
                    f"Halaman {url_path!r} seri {code}: kupon tidak valid {fields['coupon'][i]!r}: {exc}"
                )
        try:
            weighted_yield = _parse_percent_or_none(fields["weighted_yield"][i])
            maturity = _parse_id_date(fields["maturity"][i])
        except ValueError as exc:
            raise DjpprStructureError(f"Halaman {url_path!r} seri {code}: {exc}")
        btc = _parse_percent_or_none(fields["bid_to_cover"][i]) if fields["bid_to_cover"][i] is not None else None
        if weighted_yield is None:
            logger.warning(
                "Seri %s pada lelang %s (%s) tidak dimenangkan (yield '-') -- tanpa observasi yield",
                code, auction_date, url_path,
            )
        series.append(
            DjpprSeries(
                code=code,
                weighted_yield=weighted_yield,
                coupon_rate=coupon,
                maturity_date=maturity,
                bid_to_cover=btc,
            )
        )

    return DjpprAuction(
        page_id=page_id,
        url_path=url_path,
        title=title,
        auction_date=auction_date,
        settlement_date=settlement,
        series=series,
    )


def validate_pages(pages: list[object]) -> list[DjpprAuction]:
    """Validate a list of fetched pages; re-raise first structure error.

    ARCHITECTURE.md 4: failed validation must not reach transform.
    """
    return [validate_page(p) for p in pages]