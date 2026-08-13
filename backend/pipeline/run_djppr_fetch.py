"""Manual end-to-end DJPPR fetch: fetch -> validate -> transform -> store.

Fase 1 runs fetchers manually (no APScheduler yet, per PROGRESS.md).

Intentionally starts SMALL: the default window is the last 3 months. This is
the validation run -- we must prove the whole pipeline works on a few real
auctions before ever considering a full ~270-page backfill (which is a separate
decision and a later session).

Run from repo root:
    python -m pipeline.run_djppr_fetch                  # last 3 months
    python -m pipeline.run_djppr_fetch --months 6
    python -m pipeline.run_djppr_fetch --start 2024-01-01 --end 2024-06-30

Any page that fails to fetch (requests) or validate (structure) is logged as an
explicit gap, counted in the report, and does NOT abort the rest of the run
(SYSTEM.md 3 / ARCHITECTURE.md 4: no silent failures, but one bad page must
not brick the whole batch).
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime, timedelta

from db.connection import get_engine
from pipeline.fetchers.djppr import DjpprFetchError, fetch
from pipeline.storage.djppr import store
from pipeline.transformers.djppr import transform
from pipeline.validators.djppr import (
    DjpprNoAwardError,
    DjpprStructureError,
    validate_pages,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="DJPPR SUN auction fetch (small range first)")
    parser.add_argument("--months", type=int, default=3, help="window in months (default 3)")
    parser.add_argument("--start", type=_parse_date, default=None, help="start date YYYY-MM-DD")
    parser.add_argument("--end", type=_parse_date, default=None, help="end date YYYY-MM-DD")
    args = parser.parse_args()

    if args.start is not None and args.end is not None:
        start_date, end_date = args.start, args.end
        if start_date > end_date:
            parser.error("--start tidak boleh setelah --end")
    else:
        end_date = date.today()
        start_date = end_date.replace(day=1)
        # month count includes the current month; step back correctly.
        month = start_date.month - (args.months - 1)
        year = start_date.year
        while month <= 0:
            month += 12
            year -= 1
        start_date = date(year, month, 1)

    logger.info("Rentang fetch DJPPR: %s .. %s (%d bulan)", start_date, end_date, args.months)

    engine = get_engine()

    raw_pages = fetch(start_date, end_date)
    logger.info("Di-fetch: %d halaman lelang", len(raw_pages))

    validated = []
    failed_gaps: list[str] = []
    no_award_skips: list[str] = []
    for page in raw_pages:
        try:
            validated.append(validate_pages([page])[0])
        except DjpprNoAwardError as exc:
            # Cancelled auction (government accepted no bids): documented skip,
            # not a structure gap. There is genuinely no yield to record.
            no_award_skips.append(page.url_path)
            logger.warning("SKIP lelang dibatalkan %s: %s", page.url_path, exc)
        except DjpprStructureError as exc:
            failed_gaps.append(f"structure: {page.url_path} -> {exc}")
            logger.error("GAP struktur %s: %s", page.url_path, exc)
        except DjpprFetchError as exc:
            failed_gaps.append(f"fetch: {page.url_path} -> {exc}")
            logger.error("GAP fetch %s: %s", page.url_path, exc)
        except Exception as exc:  # noqa: BLE001 -- surface anything unexpected as a gap
            failed_gaps.append(f"unexpected: {page.url_path} -> {type(exc).__name__}: {exc}")
            logger.exception("GAP tak terduga pada %s", page.url_path)

    transformed = transform(validated)
    result = store(
        engine,
        transformed["bonds"],
        transformed["yield_obs"],
        fetched_at=datetime.now(),
    )

    print("\n" + "=" * 72)
    print("LAPORAN RUN DJPPR")
    print("=" * 72)
    print(f"Rentang           : {start_date} s/d {end_date}")
    print(f"Halaman di-fetch  : {len(raw_pages)}")
    print(f"Halaman valid     : {len(validated)}")
    print(f"Lelang dibatalkan : {len(no_award_skips)} (skip terdokumentasi)")
    for skip in no_award_skips:
        print(f"    - {skip}")
    print(f"GAP (gagal/parsing): {len(failed_gaps)}")
    for gap in failed_gaps:
        print(f"    - {gap}")
    print(f"Bonds upsert      : {result.bonds_written}")
    print(f"Yield observations: {result.observations_written}")
    print("-" * 72)
    for obs in transformed["yield_obs"][:12]:
        print(f"  {obs.observation_date}  {obs.bond_code:<12} yield={obs.yield_value}")
    if len(transformed["yield_obs"]) > 12:
        print(f"  ... dan {len(transformed['yield_obs']) - 12} observasi lainnya")
    print("=" * 72)
    print(f"Verifikasi manual di DB: SELECT * FROM yield_observations "
          f"WHERE source='DJPPR' ORDER BY observation_date DESC LIMIT 20;")


if __name__ == "__main__":
    main()