"""Scheduler (APScheduler) orchestrating the Fase 1 fetchers.

WHAT it does: wraps each source's fetch -> validate -> transform -> store chain
(ARCHITECTURE.md 4) into one job, and exposes a built BackgroundScheduler plus
a run-once helper. The dashboard/API NEVER invoke these jobs -- the scheduler
runs on its own cadence and writes to the DB, which the app reads
(ARCHITECTURE.md 1: pipeline disparit tegas dari aplikasi).

WHY these cadences (aligned to each source's real publication rhythm):
  - BPS IHK  : monthly (BPS publishes the national CPI roughly once a month;
               the job also re-checks whether a newer year opened on this var).
  - DJPPR    : weekly (auctions run ~every 2 weeks; a weekly sweep with a
               45-day window never relies on hitting an auction day exactly).
  - BI       : daily (JISDOR is a daily reference rate; BI7DRR updates on RDG
               days, fully covered by a rolling 90-day window).

WHY incremental windows for DJPPR/BI and full re-fetch for BPS: DJPPR listing
and BI exports must be scoped to a range (the sources can't return "only what
is new"), so the scheduler re-fetches a rolling window and relies on idempotent
upsert -- a repeated observation simply updates in place, never duplicates
(ARCHITECTURE.md 4). BPS's fetch() re-fetches all served years; YoY pairing
needs the calendar year before anyway, so a full re-fetch is both cheap and
correct.

Failure contract (SYSTEM.md 3): one failed export/page is logged as an explicit
gap and does not abort the rest of the job or the other jobs. Each job returns
a report dict (counts + gaps + ok flag) that the CLI prints and the daemon
logs, so nothing fails silently.

No interval arg needed here -- cadence lives in the trigger table below,
kept in ONE place for the CLI (run_scheduler.py) and tests to agree on.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from db.connection import get_engine
from pipeline.data.lq45_constituents import LQ45_CONSTITUENTS
from pipeline.fetchers import bi as bi_fetcher
from pipeline.fetchers import bps as bps_fetcher
from pipeline.fetchers import djppr as djppr_fetcher
from pipeline.fetchers import yahoo as yahoo_fetcher
from pipeline.storage import bi as bi_storage
from pipeline.storage import bps as bps_storage
from pipeline.storage import djppr as djppr_storage
from pipeline.storage import yahoo as yahoo_storage
from pipeline.transformers import bi as bi_transform_module
from pipeline.transformers import bps as bps_transform_module
from pipeline.transformers import bps_macro as bps_macro_transform
from pipeline.transformers import djppr as djppr_transform_module
from pipeline.transformers import yahoo as yahoo_transform_module
from pipeline.validators import bi as bi_validator
from pipeline.validators import bps as bps_validator
from pipeline.validators import bps_macro as bps_macro_validator
from pipeline.validators import djppr as djppr_validator
from pipeline.validators import yahoo as yahoo_validator

logger = logging.getLogger(__name__)

JOB_BPS = "bps"
JOB_DJPPR = "djppr"
JOB_BI = "bi"
JOB_YAHOO = "yahoo"
JOB_BPS_TRADE = "bps_trade"
JOB_BPS_PDB = "bps_pdb"
JOB_BPS_TPT = "bps_tpt"
JOB_BPS_RESERVES = "bps_reserves"

ALL_JOBS = (JOB_BPS, JOB_DJPPR, JOB_BI, JOB_YAHOO, JOB_BPS_TRADE, JOB_BPS_PDB, JOB_BPS_TPT, JOB_BPS_RESERVES)

DJPPR_WINDOW_DAYS = 45
BI7DRR_WINDOW_DAYS = 90
JISDOR_WINDOW_DAYS = 45
YAHOO_WINDOW_DAYS = 14


def run_bps_job() -> dict:
    """Fetch -> validate -> transform -> store BPS inflation YoY. Returns report."""
    try:
        engine = get_engine()
        raw = bps_fetcher.fetch()
        validated = bps_validator.validate_years(raw)
        yoy = bps_transform_module.transform(validated)
        wrote = bps_storage.store(engine, yoy, fetched_at=datetime.now())
        return {
            "job": JOB_BPS,
            "ok": True,
            "years_fetched": len(raw),
            "validated": len(validated),
            "yoy_obs": len(yoy),
            "upserted": wrote,
        }
    except Exception as exc:  # noqa: BLE001 -- record, never kill the scheduler
        logger.exception("Job BPS gagal")
        return {"job": JOB_BPS, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_djppr_job() -> dict:
    """Sweep the last DJPPR_WINDOW_DAYS for new auctions, store what's new."""
    try:
        engine = get_engine()
        end = date.today()
        start = end - timedelta(days=DJPPR_WINDOW_DAYS)

        raw_pages = djppr_fetcher.fetch(start, end)
        validated: list = []
        skips: list[str] = []
        gaps: list[str] = []
        for page in raw_pages:
            try:
                validated.append(djppr_validator.validate_pages([page])[0])
            except djppr_validator.DjpprNoAwardError as exc:
                skips.append(page.url_path)
                logger.warning("SKIP lelang dibatalkan %s: %s", page.url_path, exc)
            except djppr_validator.DjpprStructureError as exc:
                gaps.append(f"structure: {page.url_path} -> {exc}")
                logger.error("GAP struktur %s: %s", page.url_path, exc)
            except djppr_fetcher.DjpprFetchError as exc:
                gaps.append(f"fetch: {page.url_path} -> {exc}")
                logger.error("GAP fetch %s: %s", page.url_path, exc)
            except Exception as exc:  # noqa: BLE001 -- surface anything unexpected as a gap
                gaps.append(f"unexpected: {page.url_path} -> {type(exc).__name__}: {exc}")
                logger.exception("GAP tak terduga pada %s", page.url_path)

        transformed = djppr_transform_module.transform(validated)
        result = djppr_storage.store(
            engine,
            transformed["bonds"],
            transformed["yield_obs"],
            fetched_at=datetime.now(),
        )
        return {
            "job": JOB_DJPPR,
            "ok": True,
            "window": f"{start}..{end}",
            "pages_fetched": len(raw_pages),
            "pages_valid": len(validated),
            "cancelled_skips": skips,
            "gaps": gaps,
            "bonds_upserted": result.bonds_written,
            "observations_upserted": result.observations_written,
        }
    except Exception as exc:  # noqa: BLE001 -- record, never kill the scheduler
        logger.exception("Job DJPPR gagal")
        return {"job": JOB_DJPPR, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_bi_job() -> dict:
    """BI7DRR + JISDOR rolling re-fetch -> validate -> transform -> store."""
    try:
        engine = get_engine()
        today = date.today()

        exports = [
            bi_fetcher.fetch_bi7drr(today - timedelta(days=BI7DRR_WINDOW_DAYS), today),
            bi_fetcher.fetch_jisdor(today - timedelta(days=JISDOR_WINDOW_DAYS), today),
        ]
        validated: list = []
        gaps: list[str] = []
        for export in exports:
            try:
                validated.append(bi_validator.validate_xlsx(export.xlsx_bytes, export.indicator_type))
            except bi_validator.BiStructureError as exc:
                gaps.append(
                    f"structure: {export.indicator_type} {export.date_from}..{export.date_to} -> {exc}"
                )
                logger.error("GAP struktur %s", exc)
            except bi_fetcher.BiFetchError as exc:
                gaps.append(
                    f"fetch: {export.indicator_type} {export.date_from}..{export.date_to} -> {exc}"
                )
                logger.error("GAP fetch %s", exc)
            except Exception as exc:  # noqa: BLE001 -- surface anything unexpected as a gap
                gaps.append(
                    f"unexpected: {export.indicator_type} {export.date_from}..{export.date_to} "
                    f"-> {type(exc).__name__}: {exc}"
                )
                logger.exception("GAP tak terduga pada %s", export.indicator_type)

        records = bi_transform_module.transform(validated)
        counts = bi_storage.store(engine, records, fetched_at=datetime.now())
        return {
            "job": JOB_BI,
            "ok": True,
            "exports": len(exports),
            "validated": len(validated),
            "gaps": gaps,
            "upserted": counts,
        }
    except Exception as exc:  # noqa: BLE001 -- record, never kill the scheduler
        logger.exception("Job BI gagal")
        return {"job": JOB_BI, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_yahoo_job() -> dict:
    """Fetch -> validate -> transform -> store IHSG + 45 LQ45 (sequential)."""
    try:
        engine = get_engine()
        end = date.today()
        start = end - timedelta(days=YAHOO_WINDOW_DAYS)
        fetched_at = datetime.now()
        total_obs = 0
        ticker_errors: list[str] = []

        # 1. IHSG
        raw_ihsg = yahoo_fetcher.fetch(start_date=start, end_date=end)
        v_ihsg = yahoo_validator.validate_chart(raw_ihsg)
        obs_ihsg = yahoo_transform_module.transform(v_ihsg)
        r_ihsg = yahoo_storage.store(
            engine, code="^JKSE", symbol_yahoo="^JKSE",
            name="IHSG (^JKSE)", kind="index",
            observations=obs_ihsg, fetched_at=fetched_at,
        )
        total_obs += r_ihsg["obs"]

        # 2. LQ45 (sequential, errors collected)
        lq45_symbols = [c[3] for c in LQ45_CONSTITUENTS]
        multi = yahoo_fetcher.fetch_multi(lq45_symbols, start_date=start, end_date=end)
        for sym, err in multi.errors:
            ticker_errors.append(f"{sym}: {err}")

        for raw in multi.responses:
            try:
                v = yahoo_validator.validate_chart(raw)
                obs = yahoo_transform_module.transform(v)
                if obs:
                    code = v.meta.symbol.replace(".JK", "")
                    r = yahoo_storage.store(
                        engine, code=code, symbol_yahoo=v.meta.symbol,
                        name=f"{code}", kind="equity",
                        observations=obs, fetched_at=fetched_at,
                    )
                    total_obs += r["obs"]
            except Exception as exc:  # noqa: BLE001 -- collect, never abort
                ticker_errors.append(f"{raw.symbol}: {type(exc).__name__}: {exc}")
                logger.exception("Yahoo job: %s gagal proces", raw.symbol)

        report = {
            "job": JOB_YAHOO,
            "ok": True,
            "window": f"{start}..{end}",
            "ihsg_obs": r_ihsg["obs"],
            "lq45_tickers": len(lq45_symbols),
            "lq45_fetch_errors": len(multi.errors),
            "lq45_process_errors": len(ticker_errors) - len(multi.errors),
            "total_observations_upserted": total_obs,
        }
        if ticker_errors:
            report["ticker_errors"] = ticker_errors
        return report
    except Exception as exc:  # noqa: BLE001 -- record, never kill the scheduler
        logger.exception("Job Yahoo gagal")
        return {"job": JOB_YAHOO, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _run_bps_macro_job(
    job_name: str,
    fetch_fn: object,
    validate_fn: object,
    transform_fn: object,
) -> dict:
    """Generic runner for BPS macro indicator jobs (trade, pdb, tpt, reserves).

    Each follows the same pattern: fetch -> validate -> transform -> store.
    """
    try:
        engine = get_engine()
        raw = fetch_fn()
        # Filter unavailable years (e.g. 2015-2016 for trade_balance)
        available = [r for r in raw if r.body.get("data-availability") == "available"]
        unavailable = len(raw) - len(available)
        if unavailable:
            logger.info("%s: skip %d unavailable year(s)", job_name, unavailable)
        validated = validate_fn(available)
        records = transform_fn(validated)
        counts = bps_storage.store_macro(engine, records, fetched_at=datetime.now())
        return {
            "job": job_name,
            "ok": True,
            "years_fetched": len(raw),
            "years_skipped_unavailable": unavailable,
            "validated": len(validated),
            "records": len(records),
            "upserted_by_type": counts,
        }
    except Exception as exc:  # noqa: BLE001 -- record, never kill the scheduler
        logger.exception("Job %s gagal", job_name)
        return {"job": job_name, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def run_bps_trade_job() -> dict:
    """Fetch -> validate -> transform -> store trade balance (monthly)."""
    return _run_bps_macro_job(
        JOB_BPS_TRADE,
        bps_fetcher.fetch_trade_balance,
        bps_macro_validator.validate_trade_balance,
        bps_macro_transform.transform_trade_balance,
    )


def run_bps_pdb_job() -> dict:
    """Fetch -> validate -> transform -> store PDB growth (quarterly)."""
    return _run_bps_macro_job(
        JOB_BPS_PDB,
        bps_fetcher.fetch_pdb_growth,
        bps_macro_validator.validate_pdb_growth,
        bps_macro_transform.transform_pdb_growth,
    )


def run_bps_tpt_job() -> dict:
    """Fetch -> validate -> transform -> store TPT (annual)."""
    return _run_bps_macro_job(
        JOB_BPS_TPT,
        bps_fetcher.fetch_tpt,
        bps_macro_validator.validate_tpt,
        bps_macro_transform.transform_tpt,
    )


def run_bps_reserves_job() -> dict:
    """Fetch -> validate -> transform -> store foreign reserves (annual)."""
    return _run_bps_macro_job(
        JOB_BPS_RESERVES,
        bps_fetcher.fetch_foreign_reserves,
        bps_macro_validator.validate_foreign_reserves,
        bps_macro_transform.transform_foreign_reserves,
    )


_JOB_FUNCS: dict[str, object] = {
    JOB_BPS: run_bps_job,
    JOB_DJPPR: run_djppr_job,
    JOB_BI: run_bi_job,
    JOB_YAHOO: run_yahoo_job,
    JOB_BPS_TRADE: run_bps_trade_job,
    JOB_BPS_PDB: run_bps_pdb_job,
    JOB_BPS_TPT: run_bps_tpt_job,
    JOB_BPS_RESERVES: run_bps_reserves_job,
}

# One source of truth for the cadence (CLI + tests + documentation).
JOB_TRIGGERS: dict[str, CronTrigger] = {
    # BPS publishes CPI roughly monthly; day 5 07:00 local is a safe post-pub
    # moment, and the sweep also detects newly-opened years on the var.
    JOB_BPS: CronTrigger(day=5, hour=7, minute=0),
    # Weekly sweep Monday 06:30 local -- catches both auctions of a 2-week cycle.
    JOB_DJPPR: CronTrigger(day_of_week="mon", hour=6, minute=30),
    # Daily 06:00 local: JISDOR is a daily reference rate.
    JOB_BI: CronTrigger(hour=6, minute=0),
    # Daily 06:30 local: IHSG + 45 LQ45 (sequential, ~60s).
    JOB_YAHOO: CronTrigger(hour=6, minute=30),
    # BPS trade balance: monthly (BPS publishes trade data monthly; day 15 07:00).
    JOB_BPS_TRADE: CronTrigger(day=15, hour=7, minute=0),
    # BPS PDB: quarterly (BPS publishes PDB ~2 months after quarter end).
    JOB_BPS_PDB: CronTrigger(month="3,6,9,12", day=15, hour=7, minute=0),
    # BPS TPT: semi-annual (BPS publishes TPT February & August).
    JOB_BPS_TPT: CronTrigger(month="2,8", day=15, hour=7, minute=0),
    # BPS foreign reserves: monthly (follows BI publication rhythm).
    JOB_BPS_RESERVES: CronTrigger(day=15, hour=8, minute=0),
}


def run_jobs_once(jobs: list[str] | tuple[str, ...] = ALL_JOBS) -> list[dict]:
    """Run the given jobs immediately and return their reports (--run-once).

    Each job is independent: a failing job's report carries ok=False and the
    remaining jobs still run (SYSTEM.md 3: no silent gaps, one source must not
    brick the batch).
    """
    reports: list[dict] = []
    for job in jobs:
        if job not in _JOB_FUNCS:
            logger.warning("Job tidak dikenal, dilewati: %s", job)
            continue
        logger.info("RUN-ONCE mulai job %s ...", job)
        reports.append(_JOB_FUNCS[job]())
    return reports


def build_scheduler(jobs: list[str] | tuple[str, ...] = ALL_JOBS) -> BackgroundScheduler:
    """Create a configured BackgroundScheduler with one job per source.

    Each job is idempotent-safe at the storage layer (upsert), so a missed run
    can be re-run manually without duplication. max_instances=1 prevents
    overlapping runs (e.g. a slow BI job and the next daily tick).
    """
    scheduler = BackgroundScheduler()
    for job in jobs:
        if job not in _JOB_FUNCS or job not in JOB_TRIGGERS:
            logger.warning("Job/trigger tidak dikenal, dilewati: %s", job)
            continue
        scheduler.add_job(
            _JOB_FUNCS[job],
            trigger=JOB_TRIGGERS[job],
            id=f"fetch_{job}",
            name=f"fetch_{job}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )
    return scheduler