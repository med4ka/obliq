"""CLI untuk scheduler APScheduler (Fase 1).

Jalankan dari repo root:
    python -m pipeline.run_scheduler                   # daemon: jadwal harian/mingguan
    python -m pipeline.run_scheduler --run-once         # jalan-kan semua job sekali, lalu exit
    python -m pipeline.run_scheduler --run-once --jobs bps,bi   # subset

Catatan: daemon memakai BackgroundScheduler (thread) dan tetap hidup sampai
Ctrl+C. Laporan tiap job dicetak sesudah job selesai dan juga lewat logging
(PROGRESS.md: 2026 Sep–Des + BPS buka 2024+ akan masuk otomatis lewat sini).
"""
from __future__ import annotations

import argparse
import logging
import time

from pipeline.scheduler import (
    ALL_JOBS,
    JOB_TRIGGERS,
    build_scheduler,
    run_jobs_once,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _parse_jobs(value: str) -> list[str]:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    unknown = set(parts) - set(ALL_JOBS)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"job tidak dikenal: {sorted(unknown)} (pilihan: {', '.join(ALL_JOBS)})"
        )
    return parts


def _print_report(report: dict) -> None:
    print("\n" + "=" * 72)
    job = report.get("job")
    ok = report.get("ok")
    print(f"LAPORAN JOB {job.upper() if job else '?'} — {'OK' if ok else 'GAGAL'}")
    print("=" * 72)
    if not ok:
        print(f"  ERROR: {report.get('error')}")
    else:
        for key, value in report.items():
            if key in ("job", "ok"):
                continue
            print(f"  {key:<22}: {value}")
    print("=" * 72)


def _show_schedule() -> None:
    print("\nJadwal scheduler (waktu lokal):")
    for job in ALL_JOBS:
        trigger = JOB_TRIGGERS[job]
        print(f"  {job:<8} -> {trigger}")

    print(
        "\nJalankan --run-once utk test manual; "
        "kontrol via Ctrl+C utk menghentikan daemon.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Obliq scheduler (APScheduler)")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="jalankan semua job sekali lalu exit",
    )
    parser.add_argument(
        "--jobs",
        type=_parse_jobs,
        default=list(ALL_JOBS),
        help="subset job, koma-dipisah (default: semua)",
    )
    args = parser.parse_args()

    if args.run_once:
        reports = run_jobs_once(args.jobs)
        for report in reports:
            _print_report(report)
        failed = [r for r in reports if not r.get("ok")]
        if failed:
            raise SystemExit(1)
        return

    scheduler = build_scheduler(args.jobs)
    _show_schedule()
    scheduler.start()
    logger.info("Scheduler dimulai (jobs=%s). Tekan Ctrl+C untuk berhenti.", args.jobs)
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutdown scheduler...")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()