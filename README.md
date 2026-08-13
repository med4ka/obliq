# Obliq — Indonesia Capital Market Analytics Dashboard

Obliq is a data platform that collects, normalizes, and visualizes Indonesian government bond yields (SUN auction results), macroeconomic indicators (inflation, BI rate, USD/IDR, GDP, trade balance, unemployment, foreign reserves), and stock market data (IHSG index, LQ45 constituents) — all from free public sources.

Built as a solo learning project (data engineering + finance) that also genuinely serves its target audience: finance students, junior analysts, and retail investors in Indonesia who lack access to Bloomberg terminals or expensive data vendors.

---

## What Actually Works (verified)

| Feature | Status | Details |
|---|---|---|
| **Government bond yield curve** | Live, verified | 335 bonds, 1,563 yield observations from DJPPR auction data (2015–2026). Updated weekly via scheduler. |
| **Bond yield history** | Live, verified | Per-series historical yield chart. Any of 335 SUN series. |
| **Bond comparison** | Live, verified | Side-by-side yield history for 2+ bond series. |
| **Macro indicators (7 types)** | Live, verified | Inflation (YoY), BI7DRR, USD/IDR (JISDOR), GDP growth, trade balance, unemployment rate, foreign reserves. Sourced from BPS & BI. 3,606 observations total. |
| **IHSG stock index chart** | Live, verified | 44,056 daily observations (2000–present) from Yahoo Finance. |
| **LQ45 stock list & detail** | Live, verified | 45 most liquid stocks with individual history charts. |
| **Stock comparison** | Live, verified | Side-by-side price comparison for multiple stocks. |
| **Cross-category comparison** | Live, verified | `/bandingkan` — compare bonds vs stocks vs macro on a normalized base-100 scale. |
| **CSV export** | Live | Every chart has a "Unduh CSV" button — data as displayed, not whole DB. |
| **Chart expand modal** | Live | Click any chart for fullscreen view (ESC, backdrop, or X to close). |
| **Education page** | Live | Glossary of 14+ finance terms in plain Indonesian. |
| **User auth (JWT httpOnly cookie)** | Live, tested | Register, login, logout, refresh, rate-limited (5/min/IP per endpoint type). |
| **Personal watchlist** | Live, tested | Save bonds/stocks. Cross-user isolation verified. |
| **Rate limiting** | Tested | Separate buckets for auth vs watchlist (5/min/IP each). Read endpoints intentionally unrated. |
| **Scheduler (APScheduler)** | Live | Daily (BI), weekly (DJPPR), monthly (BPS) auto-fetch. Idempotent UPSERT — re-run does not duplicate. |

## Honest Limitations

- **No corporate bond credit spreads (Fase 3).** Research (Sesi 50) confirmed no free source for Indonesian corporate bond yields. IBPA (the primary source) is commercial and priced for institutions. OJK publishes only aggregate statistics, not individual yields. KSEI publishes bond metadata (registry), not market prices. Fase 3 is postponed until a viable free source emerges.
- **BPS inflation data stops at Dec 2023.** The public API has not opened 2024–2025 for the relevant variable. This is an upstream limitation, not a bug. The dashboard clearly displays "Data per Dec 2023."
- **Yahoo Finance is not an official API.** Stock data comes from Yahoo's public v8 chart endpoint — it works and is verified live, but has no SLA and could change/block without notice. Mitigations: retry backoff, Pydantic validation, DB cache (idempotent upsert).
- **LQ45 constituent list is from Wikipedia.** The official IDX list would require manual PDF download (IDX has no public API). Wikipedia data is a reasonable secondary source for a learning project — marked clearly on the page.
- **No production deployment yet.** Designed for local development. Deploy instructions are noted but not battle-tested.
- **Not real-time.** Data refreshes on scheduler cadence (daily/weekly/monthly), not streaming.
- **Not investment advice.** The dashboard presents data and context only. No buy/sell recommendations, no price targets, no scoring. This is both intentional (product scope) and a legal requirement in Indonesia (OJK regulation).
- **134 tests pass, but there is no formal coverage gate.** Fetcher HTTP layers (35–58% coverage) lack deterministic retry/timeout tests — only verified via live runs.

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Pipeline/ETL | Python (`requests`, `BeautifulSoup`/`lxml`, `Pydantic`) | Mature ecosystem for data work and scraping |
| Scheduler | `APScheduler` (current) -> cron/Airflow (future if needed) | Simple daily/weekly schedules; no over-engineering |
| Database | PostgreSQL 17 | Time-series + relational — no need for specialized TSDB at this scale |
| ORM | SQLAlchemy 2.0 + Alembic migrations | Standard Python; type-safe with `Mapped` annotations |
| API | FastAPI (Pydantic v2) | Type-safe, auto-docs, Decimal serialization via `field_serializer` |
| Frontend | Next.js 16 (App Router) + Recharts | SSR for SEO, lazy-loaded charts, DESIGN.md palette |
| Precision | Python `Decimal` (never `float`) | Non-negotiable for financial values (SYSTEM.md section 1.5) |

## Architecture

```
[External Sources: DJPPR, BPS, BI, Yahoo Finance]
        |
[Pipeline: Fetch -> Validate -> Transform -> Store]   scheduled, async from user
        |
[PostgreSQL Database -- single source of truth]
        |
[FastAPI -- read-only API layer (Pydantic responses)]
        |
[Next.js Frontend -- reads API only, never DB directly]
```

This separation is deliberate: the dashboard never waits for scraping to finish. The pipeline runs on its own schedule; users always read from the local, validated database. All financial values use `Decimal` through the entire stack — the API serializes them as exact-precision strings, not floats.

## Getting Started

### Prerequisites

- Python 3.14+ (3.12+ should work)
- Node.js 22+
- PostgreSQL 17 running locally
- A `.env` file in `backend/` (copy from `backend/.env.example`):

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/obliq_db
BPS_API_KEY=your_bps_api_key_here
JWT_SECRET=your_jwt_secret_min_32_chars
```

**BPS API key:** Register at [webapi.bps.go.id](https://webapi.bps.go.id) (free).

### 1. Backend (API + Database)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn api.main:app --reload --port 8000
```

API is now at `http://127.0.0.1:8000`. Docs at `/docs`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard at `http://localhost:3000`.

### 3. Scheduler (optional -- for auto-fetch)

```bash
cd backend
python -m pipeline.run_scheduler --run-once    # fetch & store all sources once
python -m pipeline.run_scheduler               # daemon mode (Ctrl+C to stop)
```

Or run individual fetchers:
```bash
cd backend
python -m pipeline.run_bps_fetch
python -m pipeline.run_djppr_fetch
python -m pipeline.run_bi_fetch
python -m pipeline.run_yahoo_fetch
```

### 4. Tests

```bash
cd backend && pytest -q
cd frontend && npm run lint
cd frontend && npm run build
```

## API Reference

All endpoints live under `http://127.0.0.1:8000`. OpenAPI docs at `/docs`.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness + DB connectivity |
| `/api/yield-curve/current` | GET | Latest yield per active bond (current curve) |
| `/api/yield-curve/history?bond_code=` | GET | Yield history for one bond series |
| `/api/macro/latest` | GET | Snapshot of all 7 indicators (latest per type) |
| `/api/macro/{indicator_type}` | GET | Full history for one indicator |
| `/api/stocks/list` | GET | All equity stocks with latest close & change |
| `/api/stocks/ihsg/history` | GET | IHSG daily history |
| `/api/stocks/{ticker}/history` | GET | History for one stock |
| `/api/stocks/{ticker}/latest` | GET | Latest close for one stock |
| `/api/auth/register` | POST | Register (email + password >= 6 chars) |
| `/api/auth/login` | POST | Login |
| `/api/auth/logout` | POST | Logout (clears cookies) |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/me` | GET | Current user info |
| `/api/watchlist` | GET | List user watchlist items |
| `/api/watchlist` | POST | Add item to watchlist |
| `/api/watchlist/{id}` | DELETE | Remove watchlist item |

All responses use consistent Pydantic models. Decimal values are serialized as exact-precision strings. Empty data returns `status="empty"` with a clear message — never a silent empty array.

## Project Structure

```
obliq/
  backend/               # FastAPI + data pipeline + DB migrations
    api/                 # FastAPI layer
      routers/           # yield_curve, macro, stocks, auth, watchlist
      services/          # auth_service, macro_service, stock_service, yield_service, watchlist_service
      schemas.py         # Pydantic response models
      auth.py            # JWT / password utilities
      main.py            # App factory + CORS
      dependencies.py    # get_db, get_current_user
    pipeline/            # Data ETL
      fetchers/          # bps.py, djppr.py, bi.py, yahoo.py
      validators/        # Pydantic schemas per source
      transformers/      # Normalization to internal schema
      storage/           # Idempotent DB upserts
      data/              # LQ45 constituent list
      scheduler.py       # APScheduler orchestration
      run_*.py           # CLI runners per source
    db/
      models.py          # SQLAlchemy ORM models
      migrations/        # Alembic env + 6 version files
      connection.py      # Engine bootstrap
      seed_dummy_data.py
    dashboard/           # DEPRECATED -- old Streamlit dashboard
      lib/               # api_client, charts, styling (Streamlit era)
    tests/               # pytest suite (134 tests)
      fixtures/          # bi/ (xlsx), djppr/ (html) test fixtures
    requirements.txt
    pytest.ini
    alembic.ini
    .env.example
  frontend/              # Next.js 16 App Router
    app/                 # Routes: /, /makro, /saham, /belajar, /bandingkan, /obligasi/bandingkan, /saham/[ticker], /saham/bandingkan
    components/          # UI (site-header, chart-modal, explainer-box) + chart/ (Recharts components)
    lib/                 # api-client.ts, csv-export.ts, auth-context.tsx, site-config.ts
    public/              # Static assets
    package.json, next.config.ts, tsconfig.json, eslint.config.mjs
  .venv/                 # Python virtual environment
  .gitignore
  README.md
```

## Data Sources

| Source | Data | Access Method | Status |
|---|---|---|---|
| **DJPPR** (Ministry of Finance) | Government bond auction results (yield per series) | Internal JSON API (`api-djppr.kemenkeu.go.id`) -- discovered via SPA inspection | Live, 335 bonds, 2015-present |
| **BPS** (Statistics Indonesia) | Inflation (CPI), GDP, trade balance, unemployment, foreign reserves | Official REST API (`webapi.bps.go.id`) -- free API key | Live, 7 indicator types |
| **BI** (Bank Indonesia) | BI7DRR policy rate, USD/IDR reference rate (JISDOR) | POST WebForms -> XLSX export (no headless browser needed) | Live, since 2013/2016 |
| **Yahoo Finance** (v8 chart) | IHSG index, individual stock prices (OHLC + adjusted close) | Unofficial endpoint (`query1.finance.yahoo.com/v8/finance/chart`) | Live, 44k+ obs -- NOT an official API |
| **Wikipedia** (secondary) | LQ45 constituent list | Manual snapshot (updated semi-annually) | Secondary source -- not IDX official |

**Not used** (researched and rejected): IBPA (commercial, no free tier), IDX (403 Forbidden -- no public API), Trading Economics (free tier discontinued), Investing.com (ToS forbids scraping), Google Finance (API dead since 2012).

## Project Status

| Phase | Scope | Status |
|---|---|---|
| Fase 1 | Government bond yield curve + macro indicators | Complete, audited and stable |
| Fase 2 | Corporate bond data source research | Complete -- no viable free source found |
| Fase 3 | Credit spread analytics | Postponed (depends on Fase 2 outcome) |
| Fase S1 | IHSG stock index | Complete |
| Fase S2 | Individual stock tracking (LQ45 curated list) | Complete -- 45 stocks with individual history pages |
| Fase 4 | Public launch and monetization | Not started (optional) |

**Latest audit (Sesi 51):** 134 tests passing, 0 orphans/duplicates across all tables, rate limit tested (auth/watchlist separate buckets), JWT_SECRET fail-fast verified, CORS locked (no wildcard), SQL injection scan clean, no secrets in git history, frontend builds with 0 lint errors, 8 routes HTTP 200.

---

*Dashboard data obligasi pemerintah dan saham Indonesia dari sumber resmi (DJPPR, BPS, BI) dan Yahoo Finance. Tidak ada rekomendasi investasi.*
