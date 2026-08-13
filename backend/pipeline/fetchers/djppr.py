"""DJPPR (Kemenkeu) SUN auction-result fetcher.

WHAT it fetches: Indonesian government (SUN) bond auction results from the
official DJPPR site front end:
    base = https://api-djppr.kemenkeu.go.id/web/api/v1
    POST /page/filter          -> paginated page listing (validated Sesi 7)
    GET  /page?url={slug}      -> one page's content tree (widget JSON)
The full auction table (yield, coupon, maturity, bid-to-cover per series)
arrives inside the page content as an HTML <table> in the repeater field
`@Konten` -- so the PDF on the media endpoint is NOT the primary path.

WHY two requests per auction: the listing returns each page's metadata
(PageId, UrlPath) but an EMPTY PageContentLive, so the HTML table must be
fetched per page with a second request.

Listing notes (validated live): the `page/filter` search is a fuzzy "contains"
over page content, so it returns non-auction pages (beranda, siaranpers,
pengumuman) in the same pages. Every real auction page has a UrlPath starting
with `hasillelangsuratutangnegara`, so we filter on that. Sort is newest-first
(`-dpublished`); DPublishedID is an English date like "4 Aug 2026".

CRITICAL legacy quirk (RULES.md 4): pre-CMS auction pages (auction 2021 and
older -- those rows were bulk-migrated into this CMS in Jul 2022 .. Jan 2023)
have a DPublishedID equal to the MIGRATION date, NOT the auction date. The real
auction date is embedded in the UrlPath slug ("tanggal27april2021"), so
fetch_listing filters on the slug date, never on DPublishedID alone.

Every HTTP call is honest (real User-Agent), times out, retries with
exponential backoff (SYSTEM.md 3), and sleeps between requests to stay polite
to a government server (RULES.md 1).
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api-djppr.kemenkeu.go.id/web/api/v1"
PAGE_SIZE = 50

REQUEST_TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 3
POLITE_SLEEP_SECONDS = 1.0  # between consecutive requests to djppr servers

UA = "Obliq/0.1 (data pipeline; https://github.com/yourorg/obliq; research@example.com)"

# Only auction-result pages count. Fuzzy search also returns beranda /
# siaranpers / pengumuman whose UrlPath does not start with this prefix.
AUCTION_URL_PREFIX = "hasillelangsuratutangnegara"

# English month abbreviations used by DPublishedID ("4 Aug 2026").
_EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Indonesian month names as they appear in auction URL slugs. Legacy pages
# (<=2022) hold the CMS migration date in DPublishedID, NOT the auction date;
# the real auction date is embedded in the slug as "{dd}{bulan}{yyyy}", e.g.
# "tanggal27april2021" or greenshoe "padaharirabu,14april2021". Both
# "nopember" (old spelling) and "november" appear in slugs.
_ID_MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "agustus": 8, "september": 9, "oktober": 10,
    "nopember": 11, "november": 11, "desember": 12,
}
_SLUG_DATE_RE = re.compile(
    r"(\d{1,2})(" + "|".join(_ID_MONTHS) + r")(\d{4})",
    re.IGNORECASE,
)


class DjpprFetchError(RuntimeError):
    """A fetch step failed permanently after all retries (no silent gap)."""


@dataclass(frozen=True)
class DjpprListingItem:
    """One auction page from the listing call (metadata only)."""

    page_id: int
    url_path: str
    title: str
    published: date  # from DPublishedID (for legacy: CMS migration date)
    auction_date: date | None  # AUCTION date parsed from slug (None if absent)


@dataclass(frozen=True)
class DjpprPage:
    """One auction page with its full content tree."""

    page_id: int
    url_path: str
    title: str
    content_tree: Any  # decoded PageContentLive (list of widgets)
    fetched_at: datetime


def _headers() -> dict[str, str]:
    return {"User-Agent": UA, "Accept": "application/json"}


def _post_with_retry(filters: list[dict], page_number: int) -> dict:
    url = (
        f"{API_BASE_URL}/page/filter"
        f"?operators=AND&pageNumber={page_number}&pageSize={PAGE_SIZE}"
        f"&sort=-dpublished"
    )
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = requests.post(
                url,
                json=filters,
                headers=_headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            body = resp.json()
            if not isinstance(body, dict):
                raise ValueError(f"DJPPR filter response bukan object: {type(body).__name__}")
            return body
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "DJPPR listing gagal (attempt %d/%d) page=%d: %s -- retry in %ss",
                attempt + 1, RETRY_ATTEMPTS, page_number, exc, wait,
            )
            time.sleep(wait)
    raise DjpprFetchError(
        f"DJPPR listing page {page_number} gagal setelah {RETRY_ATTEMPTS} percobaan: {last_error}"
    )


def _get_with_retry(url_path: str) -> dict:
    url = f"{API_BASE_URL}/page?url={requests.utils.quote(url_path, safe='')}"
    last_error: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = requests.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            body = resp.json()
            if not isinstance(body, dict):
                raise ValueError(f"DJPPR page response bukan object: {type(body).__name__}")
            return body
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            wait = RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "DJPPR detail gagal (attempt %d/%d) url=%s: %s -- retry in %ss",
                attempt + 1, RETRY_ATTEMPTS, url_path, exc, wait,
            )
            time.sleep(wait)
    raise DjpprFetchError(
        f"DJPPR page {url_path!r} gagal setelah {RETRY_ATTEMPTS} percobaan: {last_error}"
    )


def _parse_en_date(value: str) -> date | None:
    """Parse DPublishedID ("4 Aug 2026") -> date. Returns None if unmatched."""
    parts = value.split()
    if len(parts) != 3 or not parts[0].isdigit():
        return None
    month = _EN_MONTHS.get(parts[1].lower()[:3])
    if month is None:
        return None
    try:
        return date(int(parts[2]), month, int(parts[0]))
    except ValueError:
        return None


def _parse_slug_date(url_path: str) -> date | None:
    """Parse the AUCTION date embedded in the page's URL slug.

    Legacy pages (<=2022) publish-date to the CMS on their migration date, so
    DPublishedID is NOT the auction date. The slug always embeds the real
    auction date as "{dd}{bulan}{yyyy}" (e.g. "tanggal27april2021" or greenshoe
    "padaharirabu,14april2021"). Returns None if no date pattern is found.
    """
    match = _SLUG_DATE_RE.search(url_path)
    if match is None:
        return None
    day, month_text, year_text = match.group(1), match.group(2).lower(), match.group(3)
    month = _ID_MONTHS.get(month_text)
    if month is None:
        return None
    try:
        return date(int(year_text), month, int(day))
    except ValueError:
        return None


def _decode_content_tree(page_content_live: Any) -> Any:
    """PageContentLive is a JSON *string* holding a widget list."""
    if isinstance(page_content_live, str):
        try:
            return __import__("json").loads(page_content_live)
        except ValueError:
            return page_content_live  # already plain HTML/text, keep as-is
    return page_content_live


def fetch_listing(start_date: date, end_date: date, *, max_pages: int = 6) -> list[DjpprListingItem]:
    """Return auction pages whose AUCTION date falls within [start_date, end_date].

    The listing's DPublishedID is the CMS migration date for legacy auctions
    (pre-CMS rows were bulk-published Jul 2022 at the earliest), so it CANNOT
    be trusted as the auction date for ranges in the past. The real auction
    date is embedded in the URL slug ("tanggal27april2021"), and we filter on
    that. DPublishedID is kept as a secondary signal.

    We still page over the whole listing candidate set (newest-first by
    DPublishedID), but there is no trustworthy early-break watermark because
    legacy and modern rows are interleaved by migration date, not auction date.
    """
    filters = [
        {"Name": "PageContentLive", "Value": "Hasil Lelang Surat Utang Negara", "Condition": "contains"},
        {"Name": "Lang", "Value": "id", "Condition": "is"},
    ]
    items: list[DjpprListingItem] = []
    total_records = 0
    for page_number in range(1, max_pages + 1):
        body = _post_with_retry(filters, page_number)
        data = body.get("Data") or []
        if not data:
            break
        total_records += len(data)
        if page_number == 1:
            total_records = int(body.get("TotalRecord") or total_records)
        for row in data:
            published = _parse_en_date(str(row.get("DPublishedID", "")))
            url_path = str(row.get("UrlPath", ""))
            if not url_path.startswith(AUCTION_URL_PREFIX):
                continue
            auction_date = _parse_slug_date(url_path)
            if auction_date is None:
                logger.warning(
                    "DJPPR listing: slug tanpa tanggal lelang %r (page_id=%s) -- "
                    "pakai DPublishedID %r sebagai fallback",
                    url_path, row.get("PageId"), row.get("DPublishedID"),
                )
                auction_date = published
            if published is None and auction_date is None:
                logger.warning(
                    "DJPPR listing: DPublishedID tidak bisa diparse %r (page_id=%s) -- dilewati",
                    row.get("DPublishedID"), row.get("PageId"),
                )
                continue
            if auction_date is None:
                continue
            if start_date <= auction_date <= end_date:
                items.append(
                    DjpprListingItem(
                        page_id=int(row.get("PageId")),
                        url_path=url_path,
                        title=str(row.get("Title", "")),
                        published=published,
                        auction_date=auction_date,
                    )
                )
        time.sleep(POLITE_SLEEP_SECONDS)
    logger.info(
        "DJPPR listing: %d halaman lelang dgn tanggal lelang dalam %s..%s (dari total record %d)",
        len(items), start_date, end_date, total_records,
    )
    return items


def fetch_page_detail(item: DjpprListingItem) -> DjpprPage:
    """Fetch one auction page's content and return a DjpprPage."""
    body = _get_with_retry(item.url_path)
    data = body.get("Data") or {}
    content_tree = _decode_content_tree(data.get("PageContentLive"))
    return DjpprPage(
        page_id=int(data.get("PageId") or item.page_id),
        url_path=item.url_path,
        title=str(data.get("Title") or item.title),
        content_tree=content_tree,
        fetched_at=datetime.now(),
    )


def fetch(start_date: date, end_date: date, *, max_pages: int = 6) -> list[DjpprPage]:
    """Fetch all auction pages published within [start_date, end_date].

    Raises DjpprFetchError only if a request keeps failing after retries -- per
    SYSTEM.md 3 there is no silent skip.
    """
    listing = fetch_listing(start_date, end_date, max_pages=max_pages)
    pages: list[DjpprPage] = []
    for i, item in enumerate(listing):
        pages.append(fetch_page_detail(item))
        # Be polite between page-content requests too.
        if i < len(listing) - 1:
            time.sleep(POLITE_SLEEP_SECONDS)
    logger.info("DJPPR detail selesai: %d halaman di-fetch", len(pages))
    return pages


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    end = date.today()
    start = end.replace(month=end.month - 3) if end.month > 3 else date(end.year - 1, end.month + 9, end.day)
    result = fetch(start, end)
    print(f"Fetched {len(result)} DJPPR auction pages for {start}..{end}.")