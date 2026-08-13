"""Manual end-to-end Yahoo Finance fetch: fetch -> validate -> transform -> store.

Single symbol (default ^JKSE):
    python -m pipeline.run_yahoo_fetch
    python -m pipeline.run_yahoo_fetch --start 2024-01-01 --end 2024-03-31

LQ45 batch (sample first, then all):
    python -m pipeline.run_yahoo_fetch --sample          # 5 ticker sample
    python -m pipeline.run_yahoo_fetch --lq45             # all 45 LQ45
    python -m pipeline.run_yahoo_fetch --lq45 --start 2024-01-01 --end 2024-12-31

Flags --sample and --lq45 override --symbol (multi-ticker sequential fetch).
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime

from db.connection import get_engine
from pipeline.data.lq45_constituents import LQ45_CONSTITUENTS
from pipeline.fetchers.yahoo import YahooFetchError, fetch, fetch_multi
from pipeline.storage.yahoo import store
from pipeline.transformers.yahoo import transform
from pipeline.validators.yahoo import validate_chart

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

SAMPLE_TICKERS = [c[3] for c in LQ45_CONSTITUENTS if c[0] in ("BBCA", "BBRI", "TLKM", "ASII", "BMRI")]


def _process_one(raw, engine, fetched_at):
    """Validate -> transform -> store one symbol. Returns (ok, n_obs, symbol) or (False, error, symbol)."""
    symbol = raw.symbol
    try:
        validated = validate_chart(raw)
    except (ValueError, TypeError) as exc:
        return False, f"Validasi gagal: {exc}", symbol

    observations = transform(validated)
    if not observations:
        return True, "0 obs (skip all null-close)", symbol

    result = store(
        engine,
        code=validated.meta.symbol.replace(".JK", ""),
        symbol_yahoo=validated.meta.symbol,
        name=f"{validated.meta.symbol}",
        kind="equity",
        observations=observations,
        fetched_at=fetched_at,
    )
    return True, f"{result['obs']} obs", symbol


def main() -> None:
    parser = argparse.ArgumentParser(description="Yahoo Finance stock fetch (IHSG ^JKSE / LQ45)")
    parser.add_argument("--symbol", default="^JKSE", help="Yahoo symbol (default: ^JKSE)")
    parser.add_argument("--start", type=date.fromisoformat, default=None,
                        help="Start date YYYY-MM-DD (default: 90 days ago)")
    parser.add_argument("--end", type=date.fromisoformat, default=None,
                        help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--lq45", action="store_true",
                        help="Fetch all 45 LQ45 constituents (multi-ticker sequential)")
    parser.add_argument("--sample", action="store_true",
                        help="Fetch 5 sample LQ45 tickers (BBCA, BBRI, TLKM, ASII, BMRI)")
    args = parser.parse_args()

    engine = get_engine()
    fetched_at = datetime.now()

    if args.lq45 or args.sample:
        symbols = SAMPLE_TICKERS if args.sample else [c[3] for c in LQ45_CONSTITUENTS]
        label = "SAMPLE (5)" if args.sample else "LQ45 (45)"
        print(f"\n{'=' * 72}")
        print(f"MULTI-TICKER FETCH: {label}")
        print(f"{'=' * 72}")

        result = fetch_multi(symbols, start_date=args.start, end_date=args.end)
        total_obs = 0
        ok_count = 0

        for raw in result.responses:
            ok, detail, sym = _process_one(raw, engine, fetched_at)
            if ok:
                ok_count += 1
                total_obs += int(detail.split()[0]) if detail.split()[0].isdigit() else 0
            print(f"  {sym:15s} -> {'OK' if ok else 'GAGAL'}: {detail}")

        for sym, err in result.errors:
            print(f"  {sym:15s} -> GAGAL: {err}")

        print(f"\n--- {label} SELESAI ---")
        print(f"  Total sukses  : {ok_count}/{len(symbols)}")
        print(f"  Total gagal   : {len(result.errors)}/{len(symbols)}")
        print(f"  Total observasi: {total_obs}")
        if result.errors:
            print(f"\n  TICKER GAGAL:")
            for sym, err in result.errors:
                print(f"    {sym}: {err}")
        return

    # Single symbol (default ^JKSE)
    logger.info("Fetching %s [%s .. %s]...", args.symbol, args.start or "90d-ago", args.end or "today")
    try:
        raw = fetch(symbol=args.symbol, start_date=args.start, end_date=args.end)
    except YahooFetchError as exc:
        logger.error("Fetch gagal: %s", exc)
        return

    ok, detail, sym = _process_one(raw, engine, fetched_at)
    print(f"\n{'=' * 72}")
    print(f"LAPORAN RUN YAHOO — {sym}")
    print(f"{'=' * 72}")
    print(f"  Status: {'OK' if ok else 'GAGAL'}")
    print(f"  Detail: {detail}")


if __name__ == "__main__":
    main()
