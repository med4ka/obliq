"""Tests for pipeline/scheduler.py (APScheduler orchestration).

Covers the scheduler's contract without any network or DB:
  1. build_scheduler() registers exactly one job per source, each with the
     right trigger, max_instances=1 (no overlapping runs).
  2. A job's report reflects what fetch/validate/transform/store returned.
  3. A failing source fails loudly (ok=False with error) but the other jobs
     still run (SYSTEM.md 3: one source must not brick the batch).
  4. A structure-drift during BI/JDJPPR validation lands in `gaps`, not in a
     crash -- explicit gap, no silent skip.

The real fetchers/storage are not imported; they are replaced with stubs at the
module level (pipeline.scheduler uses module-prefixed aliases, which is why
monkeypatching the scheduler's own names handles every function).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

import pipeline.scheduler as sched


class TestBuildScheduler:
    def test_satu_job_per_sumber_dengan_trigger(self) -> None:
        scheduler = sched.build_scheduler()
        assert isinstance(scheduler, BackgroundScheduler)
        jobs = {job.id: job for job in scheduler.get_jobs()}
        assert set(jobs) == {
            "fetch_bps", "fetch_djppr", "fetch_bi", "fetch_yahoo",
            "fetch_bps_trade", "fetch_bps_pdb", "fetch_bps_tpt", "fetch_bps_reserves",
        }
        # max_instances=1 -> no overlapping runs
        assert all(job.max_instances == 1 for job in jobs.values())
        # trigger must exist (not None) so the daemon is actually scheduled
        assert all(job.trigger is not None for job in jobs.values())

    def test_subset_jobs(self) -> None:
        scheduler = sched.build_scheduler(["bi"])
        assert [job.id for job in scheduler.get_jobs()] == ["fetch_bi"]

    def test_job_tidak_dikenal_dilewati(self) -> None:
        scheduler = sched.build_scheduler(["bi", "nope"])
        assert [job.id for job in scheduler.get_jobs()] == ["fetch_bi"]


class TestJobReports:
    def test_run_bps_job_laporan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sched, "get_engine", lambda: object())
        monkeypatch.setattr(sched.bps_fetcher, "fetch", lambda: ["raw"])
        monkeypatch.setattr(sched.bps_validator, "validate_years", lambda raw: ["valid"])
        monkeypatch.setattr(sched.bps_transform_module, "transform", lambda data: ["yoy"])
        monkeypatch.setattr(sched.bps_storage, "store", lambda engine, obs, fetched_at: 1)

        report = sched.run_bps_job()
        assert report["ok"] is True
        assert report["years_fetched"] == 1
        assert report["upserted"] == 1

    def test_run_bps_job_gagal_tidak_silent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sched.bps_fetcher, "fetch", lambda: (_ for _ in ()).throw(RuntimeError("WAF banting")))

        report = sched.run_bps_job()
        assert report["ok"] is False
        assert "WAF banting" in report["error"]

    def test_run_djppr_job_laporan(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FakePage:
            url_path = "hasillelangsuratutangnegara1oktober2026"

        class FakeResult:
            bonds_written = 3
            observations_written = 9

        monkeypatch.setattr(sched, "get_engine", lambda: object())
        monkeypatch.setattr(sched.djppr_fetcher, "fetch", lambda s, e: [FakePage()] * 3)
        monkeypatch.setattr(sched.djppr_validator, "validate_pages", lambda pages: ["auction"] * 3)
        monkeypatch.setattr(
            sched.djppr_transform_module,
            "transform",
            lambda auctions: {"bonds": ["b"], "yield_obs": ["y"]},
        )
        monkeypatch.setattr(sched.djppr_storage, "store", lambda engine, b, y, fetched_at: FakeResult())

        report = sched.run_djppr_job()
        assert report["ok"] is True
        assert report["pages_fetched"] == 3
        assert report["bonds_upserted"] == 3
        assert report["observations_upserted"] == 9
        # window is a 45-day range ending today
        assert report["window"] == f"{(date.today() - timedelta(days=45))}..{date.today()}"

    def test_run_bi_job_gap_validasi_tercatat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """XLSX structure changed -> lands in gaps, not crash (SYSTEM.md 3)."""

        class FakeExport:
            indicator_type = "usd_idr"
            date_from = date(2026, 7, 1)
            date_to = date(2026, 8, 1)
            xlsx_bytes = b"not-an-xlsx"

        monkeypatch.setattr(sched, "get_engine", lambda: object())
        monkeypatch.setattr(
            sched.bi_fetcher, "fetch_bi7drr", lambda s, e: FakeExport()
        )
        monkeypatch.setattr(sched.bi_fetcher, "fetch_jisdor", lambda s, e: FakeExport())
        monkeypatch.setattr(
            sched.bi_validator,
            "validate_xlsx",
            lambda body, indicator: (_ for _ in ()).throw(
                sched.bi_validator.BiStructureError("Struktur XLSX BERUBAH")
            ),
        )
        monkeypatch.setattr(sched.bi_transform_module, "transform", lambda sheets: [])
        monkeypatch.setattr(sched.bi_storage, "store", lambda engine, recs, fetched_at: {})

        report = sched.run_bi_job()
        assert report["ok"] is True  # job tetap "selesai" dgn gap tercatat
        assert len(report["gaps"]) == 2  # 2 export, 2 gap struktur
        assert all("Struktur XLSX BERUBAH" in gap for gap in report["gaps"])
        assert report["upserted"] == {}

    def test_run_jobs_once_satu_gagal_tidak_hentikan_lain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []

        monkeypatch.setattr(sched, "_JOB_FUNCS", {
            "a": lambda: (calls.append("a") or {"job": "a", "ok": False, "error": "boom"}),
            "b": lambda: (calls.append("b") or {"job": "b", "ok": True}),
        })

        reports = sched.run_jobs_once(["a", "b"])
        assert calls == ["a", "b"]
        assert reports[0]["ok"] is False
        assert reports[1]["ok"] is True

    def test_job_tidak_dikenal_dilewati_run_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sched, "_JOB_FUNCS", {
            "b": lambda: {"job": "b", "ok": True},
        })

        reports = sched.run_jobs_once(["nope", "b"])
        assert [r["job"] for r in reports] == ["b"]  # "nope" di-log, tidak dipanggil