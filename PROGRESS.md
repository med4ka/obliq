# PROGRESS TRACKER — OBLIQ

> File ini WAJIB dibaca AI di awal SETIAP sesi, dan WAJIB di-update di akhir SETIAP sesi. Ini "memori kerja" antar sesi — pola yang sama seperti project-project sebelumnya (Selaras, NusaPath).

## Status Saat Ini
**Fase aktif:** Fase 1 — Kurva Yield Pemerintah + Makro. **BACKEND SEDANG BERJALAN & TERAUDIT (Sesi 19)** — 84 test hijau, idempotency 3x TERUJI, gap handling TERUJI, integritas data clean, tidak ada secret ter-commit. **GIT REPO AKTIF (Sesi 20):** commit pertama `7f2eea8` "Fase 1 backend OBLIQ: pipeline kurva yield & makro (audited & stable)" (69 files, 8k baris); `.env` TERVERIFIKASI tidak ter-track, `git status` bersih; BELUM ada remote (keputusan push terpisah nanti). Selanjutnya utk Fase 1: dashboard Streamlit (kurva yield + indikator makro) & gap handling di dashboard.
**Terakhir dikerjakan:** Sesi 20 — `git init` root + commit pertama; `.gitignore` diperkuat (`.coverage`, `.coverage.*`); `.env`/`.venv`/`__pycache__` terverifikasi lewat `git ls-files` TIDAK ada di index; fixture HTML/XLSX hasil observasi sumber dibukukan (bukan cache scraping runtime — fetcher parse in-memory). Detail di item "Sesi 20" di bawah.
**Update terakhir:** 2026-08-11

---

## Fase 0 — Setup & Riset Awal 🚧 BERJALAN

> Ini fase paling penting untuk divalidasi duluan — kalau sumber data ternyata tidak bisa diakses seperti yang diasumsikan, seluruh rencana perlu direvisi SEBELUM banyak kode ditulis.

### Checklist
- [x] Setup repo: struktur folder sesuai ARCHITECTURE.md §3, venv (`.venv/` + `requirements.txt`), `.env` dengan `DATABASE_URL`
- [x] Koneksi PostgreSQL lokal teruji — `obliq_db` (PG 17, localhost trust auth, user `postgres`)
- [x] Keamanan DB: role terbatas `obliq_app` dibuat (LOGIN, password), grant ONLY ke `obliq_db` (CONNECT + schema public + CRUD + default privileges utk tabel migrasi Fase 1). `.env`/`.env.example` pakai role baru. Teruji: connect + baca + write (seed) sebagai `obliq_app`
- [x] `postgresql.conf` diubah: `listen_addresses = 'localhost'` + restart service PG — teruji post-restart koneksi `obliq_app` tetap jalan, port 5432 cuma listen `127.0.0.1`/`::1`
- [x] Dashboard minimal: `dashboard/app.py` render `macro_indicators` + badge "DATA CONTOH — BELUM DARI SUMBER RESMI" utk source DUMMY/kosong — teruji via Streamlit AppTest (6 baris, 0 exception)
- [x] Registrasi API key BPS **dicoba & BLOKIR WAF** (lihat "Diketahui Bermasalah") — `webapi.bps.go.id` kenanya bot/VPN detection, belum tentu API-nya sendiri diblok
- [x] Seed data dummy `macro_indicators` (`source='DUMMY_CONTOH'`) untuk development dashboard sebelum data asli ada — `python -m db.seed_dummy_data` (idempoten: re-run cuma ganti baris DUMMY)
- [x] Dapatkan API key BPS **& TERUJI** — Ghif login manual tanpa VPN sukses (WAF cuma blokir tooling/VPN), key di `.env`, run fetcher nyata berhasil (Sesi 6)
- [x] Riset manual DJPPR: struktur data hasil lelang SUN (lihat ringkasan di bawah)
- [x] Riset manual BI: BI7DRR & kurs referensi (lihat ringkasan di bawah)
- [x] **Validasi live akses BI (Sesi 15):** BI7DRR & JISDOR export XLSX via POST WebForms — format file & filter periode TERUJI. Data mulai 2013-05-20 (JISDOR) / 2016-04-21 (BI7DRR). (Update di "Hasil Riset Manual Sumber Data".)
- [x] **Keputusan checkpoint Fase 0:** sumber BPS tervalidasi penuh (fetcher jalan). DJPPR (PDF via api-media) & BI (HTML table) sudah di-riset strukturnya — validasi format persis menunggu Fase 1 fetch pertama. Dilanjutkan Fase 1 (sudah dimulai sesi ini dengan BPS).

### Hasil Riset Manual Sumber Data (Sesi 5 → DIREVISI Sesi 7)
**DJPPR Kemenkeu — skor akses: MUDAH–MENENGAH (tabel HTML di JSON API internal — PDF hanya backup):**
- Asumsi awal Sesi 5 ("hasil lelang = PDF via `media/{GUID}`, perlu parse PDF") **TERBUKTI SALAH / terlalu pesimis**. Validasi Sesi 7 menemukan endpoint CMS internal yang mengembalikan tabel hasil lelang langsung sebagai JSON, sudah berstruktur. PDF tetap ada tetapi redundan.
- Situs `djppr.kemenkeu.go.id` adalah Angular SPA (CMS "cms-studio-front-v2"). `robots.txt` mengembalikan HTML SPA, bukan robots.txt asli. Host API benar: `api-djppr.kemenkeu.go.id` (www gagal TLS; butuh Tls12 + UA browser).

**Bank Indonesia — skor akses: MUDAH (Sesi 15 — DIREVISI dari asumsi Sesi 5, TERUJI LIVE):**
- **BI7DRR** di `bi.go.id/id/statistik/indikator/bi-rate.aspx` (WebPart `ctl00_ctl54_g_78f62327_0ad4_4bb8_b958_a315eccecc27`) — filter periode (Dari/Sampai, format `dd/mm/yyyy`, kontrol `TextBoxDateStart`/`TextBoxDateEnd`) + tombol **Unduh**. Tombol Unduh = POST standar ASP.NET WebForms → **balikin file XLSX nyata** (`BI-7Day-RR.xlsx`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), kolom `NO | Tanggal | BI-7Day-RR`. Nilai `4.75 %` (dengan spasi), tanggal format Indonesia ("22 Juli 2026"). **TIDAK perlu headless browser, TIDAK perlu pagination** — POST pakai `__VIEWSTATE`+`__EVENTVALIDATION`+`__VIEWSTATEGENERATOR` dari GET pertama.
- **Kurs JISDOR (USD/IDR)** di `bi.go.id/id/statistik/informasi-kurs/jisdor/default.aspx` (WebPart `ctl00_ctl54_g_f51e6b6d_47c5_4ff4_8105_27cbd1a2f52d`) — filter periode (`TextBoxFrom`/`HiddenFieldDateFrom`/`TextBoxDateTo`/`HiddenFieldDateTo`) + tombol **Unduh** (`ButtonExport`, class `btn-export`). POST sama → **XLSX** (`Informasi Kurs Jisdor.xlsx`), kolom `NO | Tanggal | Kurs`. Kurs integer Rupiah (`17913`, tanpa desimal), tanggal serial US `8/7/2026 12:00:00 AM` (parse manual). Filter periode di-EXPORT benar-benar berlaku (2016 narrow = 9 baris, 2020-2021 = 24 baris).
- **Jangkauan data teruji (Sesi 15):** JISDOR ada mulai **2013-05-20** (2011-2012 = XLSX kosong), BI7DRR mulai **2016-04-21** (2000-2012 = kosong; BI7DRR memang diluncurkan 2016). Total full-range JISDOR 2010-2026 = **3198 baris** (≈batas export, jadi fetch per-tahun/chunk lebih aman); BI7DRR full = 126 baris (RDG).
- `data.go.id` alternatif tidak perlu — export XLSX langsung sudah cukup. `dataapi.bi.go.id/dataexchange/v1` (disebut riset GitHub lain) **tidak resolve DNS** — bukan jalur valid.
- `robots.txt` bi.go.id = `Allow: /` (hanya disallow `/_layouts`, `/Style Library`, dst — halaman statistik boleh di-crawl). Rate-limit sopan tetap wajib.
- Implikasi Fase 1: fetcher BI = GET halaman (ambil hidden fields) → POST dengan rentang tanggal + `ButtonExport` → simpan XLSX → parse dengan stdlib (zipfile+ElementTree, sharedStrings inline) — TIDAK perlu dependency openpyxl. Validasi format XLSX sudah diverifikasi Sesi 15.

### Cara Verifikasi
Berhasil fetch minimal 1 data point nyata dari BPS, DJPPR, dan BI secara manual (script kecil, belum perlu pipeline penuh) sebelum dianggap fase ini selesai.

---

## Fase 1 — Kurva Yield Pemerintah + Makro 🚧 BERJALAN

> Rujukan: PRD.md §5 Fase 1, SCHEMA.md untuk skema tabel

### Selesai
- [x] Model DB formal: `db/models.py` (SQLAlchemy 2.0 `Mapped`) + migration Alembic pertama (`c33a23e70646`) untuk `macro_indicators`. Keputusan: tabel dummy yang sudah ada **tidak perlu di-drop/altered** — struktur bootstrap DDL ternyata IDENTIK dengan model formal (kolom + unique constraint `uq_macro_type_date` sudah benar), migration dibuat via autogenerate lalu di-edit idempoten (checkfirst: no-op di DB yang sudah ada, create di DB fresh). `alembic upgrade head` sukses, `alembic_version` tercatat.
- [x] Fetcher BPS (`pipeline/fetchers/bps.py`) — **TERUJI JALAN NYATA**: fetch IHK nasional var_id=1709 (bukan 2 — lihat catatan), 4 tahun (2020-2023), timeout+retry backoff.
- [x] Validator BPS (`pipeline/validators/bps.py`) — skema Pydantic respons mentah; 10 pytest hijau.
- [x] Transformer BPS (`pipeline/transformers/bps.py`) — parse Decimal + hitung inflasi YoY (rumus manual), gap di-skip dengan log jelas (tidak interpolasi).
- [x] Storage BPS (`pipeline/storage/bps.py`) — upsert `ON CONFLICT (indicator_type, observation_date) DO UPDATE`, idempoten (re-run = 36 baris, bukan dobel).
- [x] `pipeline/run_bps_fetch.py` — orkestrasi manual fetch→validate→transform→store. **Hasil run nyata (Sesi 6): 36 baris YoY Jan 2021–Des 2023, source='BPS'**, verifikasi di DB berhasil; nilai sesuai angka resmi BPS (Jan-2021=1.55%, Okt-2023=2.56%, Des-2023=2.61%).
- [x] Model DB bonds/issuers/yield_observations (`db/models.py`) + migration `a1b2c3d4e5f6` — `bonds.code` UNIQUE, `yield_observations` UNIQUE (bond_id, observation_date). `alembic upgrade head` sukses di DB live.
- [x] Fetcher DJPPR (`pipeline/fetchers/djppr.py`) — **TERUJI JALAN NYATA**: listing `POST /page/filter` (filter UrlPath prefix `hasillelangsuratutangnegara` + rentang tanggal dari DPublishedID "4 Aug 2026"), detail `GET /page?url=` per halaman, timeout+retry backoff, sleep sopan 1s antar request.
- [x] Validator DJPPR (`pipeline/validators/djppr.py`) — parse `@Konten` HTML `<table>` via BeautifulSoup (lxml), keyed by label (order-independent), **berhenti explicit** via `DjpprStructureError` kalau struktur kolom berubah/mismatch. Pydantic `DjpprAuction`/`DjpprSeries`.
- [x] Transformer DJPPR (`pipeline/transformers/djppr.py`) — 1 lelang → N seri → 1 bond per kode + 1 observasi per (seri, tanggal); Decimal semua; seri tidak-dimenangkan ("-") di-skip (double log validator), tenor_years dari maturity−auction, issue_date None (reopen tidak disclose tanggal issue asli).
- [x] Storage DJPPR (`pipeline/storage/djppr.py`) — upsert bonds by code (RETURNING id), lalu yield_observations by (bond_id, observation_date); idempoten.
- [x] `pipeline/run_djppr_fetch.py` — orkestrasi manual dengan rentang kecil. **Hasil run nyata (Sesi 8): rentang Jun 1–Agu 10 2026 → 5 lelang, 19 bonds, 42 yield_observations (source='DJPPR')**, 3 seri "-" di-skip, 0 gap, re-run tetap 19/42 (tidak dobel).

### Belum Dibuat
- [x] **Fetcher BI (BI7DRR, kurs USD/IDR) (Sesi 16)** — akses & format XLSX sudah divalidasi (Sesi 15); pipeline lengkap (fetcher+validator+transformer+storage+runner) TERUJI JALAN NYATA.
- [x] **Backfill BI PENUH (Sesi 16)** — BI7DRR 126 obs (2016-04-21..2026-07-22), JISDOR 3198 obs (2013-05-20..2026-08-07), keduanya source='BI', 0 gap, idempoten.
- [x] **API FastAPI read-only (Sesi 17)** — 5 endpoint: `GET /health`, `GET /api/yield-curve/current` (kurva terkini per bond aktif), `GET /api/yield-curve/history` (histori 1 bond, rentang opsional), `GET /api/macro/latest` (snapshot semua indikator), `GET /api/macro/{indicator_type}` (histori 1 indikator, rentang opsional). Pola router→service→db (session via `Depends(get_db)`, TIDAK akses langsung di router). Decimal→string presisi via Pydantic `field_serializer`; per item selalu `source`+`fetched_at`+`observation_date` (audit trail); dummy ter-tag `is_dummy`+`notice`; kosong → `status="empty"`+`message` jelas (bukan silent []), rentang terbalik → HTTP 422, error internal → 500 jelas. **72 test hijau (+14 API), uvicorn live `/docs` OK.**
- [x] **Scheduler APScheduler (Sesi 18)** — `pipeline/scheduler.py` (job per sumber: fetch→validate→transform→store, laporan per-job, gap per-halaman/sheet tercatat di `gaps` BUKAN crash, 1 sumber gagal tidak menghentikan yang lain — SYSTEM.md 3) + `pipeline/run_scheduler.py` (CLI: `--run-once`, `--jobs`, daemon). Jadwal sesuai ritme sumber: BPS bulanan tgl-5 07:00 (sekaligus deteksi tahun baru dibuka), DJPPR mingguan Senin 06:30 (window 45 hari), BI harian 06:00 (BI7DRR 90 hari, JISDOR 45 hari). `fetch()` BPS dukung `years=[...]` (tahun tak didukung di-skip). **84 test hijau (+13), `--run-once` TERUJI LIVE: BPS 36 YoY, DJPPR 14 bonds/25 obs, BI 4+32 (JISDOR 2026-08-10 baru); DB idempoten (DJPPR tetap 1563, BI 3325, tidak dobel).**
- [x] **Backfill DJPPR 2021 (Sesi 10)** — apr–des 2021 = 15 lelang, 29 bonds, 103 obs, 0 gap. (Sisa historis: 2020 dan lebih tua; lihat catatan sesi 7)
- [x] **Backfill DJPPR 2015 (Sesi 11)** — rentang awal DIVERIFIKASI (bukan asumsi) = 2015-11-10; 2015 awalnya 3 lelang, 9 bonds, 13 obs, 0 gap. **REVISI Sesi 14:** 3 slug SPN ternyata lelang 2015 → 2015 jadi **6 lelang, 26 obs**, rentang awal mundur ke **2015-05-26**.
- [x] **Backfill DJPPR 2016 (Sesi 12 + recover Sesi 13/14)** — 21 lelang awal, 95 obs; +recover 2016-01-05 (page 3554) via window 2022 → **22 lelang, 100 obs**. 4 slug SPN tanpa tanggal awalnya dilewati dengan log (page_id 3976/3968/3891/3554); ternyata 3554 = lelang 2016, 3 sisanya = lelang 2015 (Sesi 14).
- [x] **Backfill DJPPR 2017 (Sesi 13)** — 23 lelang, 39 bonds, 117 obs, 0 gap.
- [x] **Backfill DJPPR 2018 (Sesi 13)** — 22 lelang valid + **1 SKIP terdokumentasi** (lelang 08-Mei-2018 DIBATALKAN, Pemerintah tidak menerima semua penawaran → `DjpprNoAwardError`, bukan gap struktur), 40 bonds, 118 obs, **0 hard gap**.
- [x] **Backfill DJPPR 2019 (Sesi 13)** — 21 lelang, 40 bonds, 142 obs, 0 gap. (1 seri "-" pada 21-Mei-2019 di-skip.)
- [x] **Backfill DJPPR 2020 (Sesi 13)** — 25 lelang, 37 bonds, 165 obs, 0 gap. (7 seri "-" di-skip, termasuk FR0076 di 2 lelang.)
- [x] **Backfill DJPPR 2022 (Sesi 13)** — 29 halaman fetch (27 tanggal lelang unik, ritme 2-mingguan), 47 bonds (2022-only), 177 obs, 0 gap. Termasuk halaman tanggal-ganda (`12april2022dantanggal13april2022`) & seri sukuk `FRSDG001`; efek bonus: halaman SPN-slug 2016 (page 3554, fallback DPublishedID 22-Des-2022) auto-recover → obs 2016-01-05 terisi (5 obs: FR0053/56/72, SPN12160401, SPN12170106).
- [x] **Backfill DJPPR 2023 (Sesi 14)** — gap Jan 2023–Mei 2026 resmi DITUTUP. 27 halaman di-fetch (24 lelang 2023 + recover 3 SPN-slug), 24 tanggal lelang 2023, 153 obs, 0 gap. Bonus: 3 slug SPN-2016 tersisa (page 3976/3968/3891) ternyata berisi lelang **2015** (2015-05-26, 2015-10-13, 2015-10-27) → rentang awal DJPPR mundur ke **2015-05-26**.
- [x] **Backfill DJPPR 2024 (Sesi 14)** — 24 lelang, 156 obs, 0 gap.
- [x] **Backfill DJPPR 2025 (Sesi 14)** — 24 lelang, 177 obs, 0 gap.
- [x] **Backfill DJPPR 2026 Jan–Mei (Sesi 14)** — 10 lelang, 87 obs, 0 gap — nyambung mulus ke 2026 Jun–Agu (Sesi 8, 5 lelang/42 obs). 2026 total jadi 15 lelang/129 obs.
- [x] **Backfill DJPPR SELESAI TOTAL (Sesi 14)** — FINAL: **335 bonds, 1563 yield_observations**, rentang **2015-05-26 s.d. 2026-08-04**, **KONTINU tanpa bulan kosong**. Checkpoint per rentang: tanpa DjpprStructureError baru di 2023/2024/2025/2026 (semua pola approved jalan).
- [ ] Fetcher BPS: perpanjang jangkauan sampai tahun terbaru (cek kapan BPS "buka" 2024/2025 di var ini)
- [x] **Scheduler (APScheduler) — Selesai (Sesi 18)** — jadwal fetch otomatis sesuai frekuensi update masing-masing sumber: BPS bulanan, DJPPR mingguan, BI harian (detail di STATUS HEAD + checklist Selesai).
- [ ] API FastAPI lanjutan yang belum ada di Sesi 17: belum ada rate-limit/auth (SENG AJA, itu Fase 4 — dicatat di "Diketahui Bermasalah"); belum ada endpoint bonds metadata tersendiri (kurva current sudah bawa bond_code/tenor/coupon/maturity).
- [ ] Dashboard Streamlit: halaman kurva yield (chart utama), halaman indikator makro, halaman "Belajar" (glossary dari PRD.md §1)
- [ ] Gap handling teruji: matikan 1 fetcher secara sengaja, pastikan dashboard menampilkan gap dengan benar (bukan crash, bukan data palsu)

### Temuan Penting Riset Live API BPS (Sesi 6 — VALIDASI, bukan asumsi)
- `var_id=2` ("IHK Umum") Cuma berisi **1979–2019** (basis lama 2012). Angka IHK modern (>2019) TIDAK ada di var ini.
- Yang benar untuk IHK Nasional terkini: **`var_id=1709` "Indeks Harga Konsumen 90 Kota (Umum)", basis 2018=100**, `vervar=9999` ("INDONESIA").
- API **tidak mendukung range** `th/2023:2025` (balikin `list-not-available`) — tiap tahun = 1 request pakai `th_id` (bukan tahun: 2020=120 … 2023=123). Mapping th_id→tahun didapat dari endpoint th list.
- Format `datacontent`: key `{vervar}{var}{th_id:04d}{month}`, value bisa string ATAU float JSON — wajib `Decimal(str(v))`.
- Ketersediaan terbaru di API untuk var 1709: **cuma sampai 2023** (2024/2025 `list-not-available`). Perlu dipantau pas BPS buka tahun baru.

### Temuan Riset Live API DJPPR (Sesi 7 — VALIDASI, REVISI asumsi Sesi 5)
**Endpoint (semua `base = https://api-djppr.kemenkeu.go.id/web/api/v1`, butuh Tls12 + UA browser):**
- **Listing:** `POST /page/filter?operators=AND&pageNumber={n}&pageSize=50&sort=-dpublished`, body `[{"Name":"PageContentLive","Value":"Hasil Lelang Surat Utang Negara","Condition":"contains"},{"Name":"Lang","Value":"id","Condition":"is"}]`, Content-Type JSON. Response `{Data:[{PageId,Title,UrlPath,DPublishedID,...}], TotalPage, TotalRecord}`. Hasil teruji sesi 7: TotalRecord=270. **REVISI Sesi 9:** TotalRecord bisa lebih besar dari jumlah baris yang benar-benar dikembalikan (header kadang 490), dan `DPublishedID` utk halaman lama = tanggal migrasi CMS (Jul 2022–Jan 2023), BUKAN tanggal lelang → filter rentang wajib pakai tanggal dari slug. Listing ikut membawa halaman non-lelang (beranda/pengumuman/siaran pers) — filter prefix `UrlPath` = `hasillelangsuratutangnegara`. Data historis membentang **s.d. 2015** (bukan cuma Apr 2021 seperti catatan awal).
- **Konten halaman:** `GET /page?url={slug}` (slug = `UrlPath`, URL-encoded) → `{Data:{Title,PageId,PageContentLive (JSON string widget tree)}}`.
- **Media:** `GET /media/{GUID}` → PDF binary (endpoint eksis, 400 utk GUID invalid). Dipakai untuk file keterangan pers.

**Bentuk data hasil lelang (TEMUAN KUNCI):** tabel hasil lelang **SUDAH ADA sebagai HTML `<table>` di dalam field `@Konten`** widget `repeater` pada `PageContentLive` — TIDAK perlu PDF/OCR. Terverifikasi konsisten pada halaman 2026-08-04 (9 seri: SPN01260905…FR0105) dan 2023-12-12 (7 seri: SPN03240313…FR0089). Row layout per halaman bervariasi (beberapa halaman punya baris extra "Yield tertinggi/terendah yang masuk", "Nominal kompetitif yang dimenangkan", dst.).
- **Kolom per seri (label konsisten bahasa Indonesia):** Yield rata-rata tertimbang yang dimenangkan, Yield tertinggi/terendah dimenangkan, Tingkat kupon, Tanggal jatuh tempo, Jumlah nominal dimenangkan, Jumlah penawaran yang masuk, Bid-to-cover-ratio, Tanggal setelmen/penerbitan.
- **PDF (backup, bukan wajib):** unduhan `media/{GUID}` teruji 235KB, **teks ter-ekstrak penuh** via pdfplumber (tabel rapi, 2663 chars, 2 tables deteksi otomatis) — bukan scan, tak butuh OCR.
- Halaman `ringkasanhasilpenerbitan` (PageId 1230) hanya teks format (lelang reguler/bookbuilding/private placement), tabel ringkasannya di file lampiran media — bukan sumber langsung.
- **Rekomendasi keputusan untuk fetcher DJPPR:** (1) LISTING via `/page/filter` (270 halaman, sinkron naik bertahap), (2) KONTEN via `/page?url=` → parse HTML `<table>` di `@Konten` (decisive data: per seri + yield rata-rata tertimbang + kupon + jatuh tempo + bid-to-cover), (3) PDF `media/{GUID}` opsional sbg fallback/keterangan pers. PDF parsing TIDAK wajib. Struktur row HTML perlu kelola variasi antar halaman (mis. regex/kunci tabel by label).

---

## Fase 2 — Riset Sumber Data Korporasi 🚧 BELUM DIMULAI

### Belum Dibuat
- [ ] Riset: keterbukaan informasi OJK untuk obligasi korporasi — data apa yang dipublikasi dan seberapa sering
- [ ] Riset: prospektus IDX untuk obligasi tercatat — apakah ada data harga/yield yang bisa diambil
- [ ] Riset: opsi data pihak ketiga dengan free tier (Investing.com, Trading Economics, dst) sebagai fallback
- [ ] **Keputusan checkpoint:** dokumentasikan hasil riset ini di sini, dan putuskan Fase 3 lanjut dengan sumber apa (atau scope dikurangi/diubah)

---

## Fase 3 — Credit Spread Analytics 🚧 BELUM DIMULAI (tergantung Fase 2)

### Belum Dibuat
- [ ] Model database: `bonds` (extend untuk corporate), `issuers`, `credit_spreads`, `anomaly_flags`
- [ ] Fetcher data korporasi (sesuai hasil riset Fase 2)
- [ ] Service kalkulasi spread (cocokkan tenor ke benchmark pemerintah terdekat)
- [ ] Anomaly detection sederhana (perubahan spread > threshold dalam periode tertentu)
- [ ] Dashboard: halaman per emiten, chart spread historis, daftar anomaly flag (bahasa netral, DESIGN.md §5)

---

## Fase 4 — Publik & Monetisasi 🚧 BELUM DIMULAI (opsional)

### Belum Dibuat
- [ ] Auth (reuse pola JWT httpOnly cookie dari project sebelumnya)
- [ ] Watchlist personal
- [ ] Keputusan model tier gratis vs berbayar
- [ ] Deploy (ARCHITECTURE.md §6)

---

## Diketahui Bermasalah / Belum Dites ⚠️
- ~~**PostgreSQL `listen_addresses='*'`**~~ → **RESOLVED** (Sesi 5): diubah ke `localhost`, service di-restart, koneksi `obliq_app` terverifikasi tetap jalan, port 5432 sekarang cuma `127.0.0.1`/`::1`.
- ~~**BPS WebAPI — registrasi diblokir WAF**~~ → **RESOLVED** (Sesi 6): Ghif login manual + generate API key, key sudah di `.env` dan **teruji jalan** dari fetcher (4 tahun fetch sukses). Catatan sesi sebelumnya soal Support ID 6575722619588719224 jadi invalid — WAF cuma blokir akses dari tooling/VPN, bukan dari browser biasa.
- **BPS IHK var 1709 hanya tersedia s.d. 2023 di API** — 2024/2025 belum "dibuka" BPS untuk var ini. Dampak: inflasi YoY termuda yang bisa dihitung = Des 2023. Bukan bug fetcher; gap karena sumber (perlu dipantau & hindari salah kaprah "data terbaru"). Dashboard mesti tampilkan "data per Des 2023" dengan jelas (SYSTEM.md §1 poin 3).
- **DJPPR `/robots.txt` mengembalikan HTML SPA, bukan robots.txt asli** (kemungkinan karena Angular SPA config) — perlu dicek manual via browser sebelum menganggap site terbuka untuk scraping. Fetcher sudah sopan (UA jujur + sleep 1s antar request) sebagai mitigasi.
- **DJPPR listing filter itu fuzzy "contains"** — ikut membawa halaman non-lelang (beranda/siaranpers/pengumuman); sudah di-filter lewat prefix `UrlPath` = `hasillelangsuratutangnegara`. CATATAN: halaman lelang "green shoe" (tambahan) juga diawali prefix ini — tercakup (bagus), tapi formatnya perlu dipantau.
- **Seri "-" (tidak dimenangkan)** di data DJPPR — sudah ditangani (skip + log), bukan bug.
- **Lelang DIBATALKAN (no award)** di data DJPPR — kasus nyata 08-Mei-2018 (PageId 3146): Pemerintah memutuskan "tidak menerima semua penawaran", jadi memang **tidak ada** tabel hasil / yield yang bisa dicatat. Ditangani lewat `DjpprNoAwardError` (subclass `DjpprStructureError`) yang di-skip+dilog secara terdokumentasi di runner — BUKAN gap struktur. Judul kasus: normal.
- ~~**2023..2025 kosong (Sesi 13)**~~ → **RESOLVED (Sesi 14)**: gap Jan 2023–Mei 2026 DITUTUP penuh; kurva DJPPR kontinu 2015-05-26..2026-08-04. 3 slug SPN tersisa ternyata lelang 2015 (bukan 2016) dan sudah ter-recover.
- **2026 Sep–Des belum di-backfill** — data berjalan (hari ini 10-Agu-2026); **kini masuk otomatis via scheduler (Sesi 18)**. Backfill manual hanya dibutuhkan kalau ada rentang lama yang belum pernah di-fetch.
- ~~**`dataapi.bi.go.id` (API data portal BI yang disebut di riset GitHub) TIDAK resolve DNS**~~ → **RESOLVED (Sesi 16):** jalur mati itu tidak dipakai; jalur valid yang kini berfungsi penuh = export XLSX via POST WebForms di `www.bi.go.id` (Sesi 15) → `pipeline/fetchers/bi.py` TERUJI LIVE.
- ~~**BI: export XLSX punya batas baris**~~ → **RESOLVED (Sesi 16):** fetch per-tahun menghindari cap ~3200 baris; backfill JISDOR 2013-2026 per tahun (14 export) = 3198 obs lengkap.
- ~~**BI: format tanggal/kurs XLSX perlu parse manual**~~ → **RESOLVED (Sesi 16):** parser tanggal US serial, tanggal Indonesia, persen dengan spasi ditangani `pipeline/transformers/bi.py`; diuji 58 test hijau.
- **API belum ada auth / rate-limit** — SENG AJA di sesi ini, sesuai scope Fase 1 (PRD.md §5: auth = Fase 4). API saat ini read-only dan belum ditutup; kalau nanti dibuka publik wajib rate-limit + API key (ARCHITECTURE.md §5). Catatan juga diketik ketat di `api/main.py` + `api/routers/*` (tidak pernah lakukan `os.getenv` duplikat / tidak ada session leak — dependency `get_db` menutup session per request).
- (Lainnya kosong — seed dummy tetap 6 baris DUMMY_CONTOH, TIDAK dihapus sesuai instruksi, dan source-nya beda dari BPS jadi bisa dibedakan dashboard.)

## Keputusan Teknis yang Sudah Diambil (dan kenapa)
> Lihat RULES.md §3 untuk detail lengkap. Ringkasan: Decimal bukan float, pipeline-app dipisah tegas, gap tidak diinterpolasi diam-diam, Streamlit untuk MVP, tidak ada rekomendasi beli/jual.
- Tambahan sesi 6: semua data yang dirender WAJIB punya `source` jelas; `source` kosong/`DUMMY*` = badge "DATA CONTOH — BELUM DARI SUMBER RESMI", tidak boleh dicampur rata dengan data asli (RULES.md §3).
- Tambahan sesi 8 (DJPPR): `issue_date` bonds dibiarkan NULL (reopen/re-issuance tidak mengungkap tanggal issue asli; mengisi = fabrikasi — SYSTEM.md §1). `tenor_years` dihitung dari maturity−tanggal lelang per observasi (bukan dari issue). Seri tidak-dimenangkan ("-") tidak dicatat observasi (tidak ada yield yang valid), bond-nya juga tidak di-create kalau cuma muncul sebagai "-".
- Tambahan sesi 13 (DJPPR): lelang yang DIBATALKAN total (Pemerintah "tidak menerima semua penawaran") = `DjpprNoAwardError` — status DATA (bukan struktur), di-skip+log di runner seperti slug SPN tanpa tanggal. Guard frasa dipasang SEBELUM parse tabel; kelewat di regex → tetap jatuh ke `DjpprStructureError` (selalu aman, tidak pernah parse salah diam-diam).
- Tambahan sesi 17 (API): **layer aplikasi memakai respons Pydantic, bukan FastAPI `jsonable_encoder`** — `jsonable_encoder` FastAPI mengubah `Decimal` jadi `float` (danger), sedangkan Pydantic v2 `response_model` + `field_serializer` mengeluarkan string presisi. Semua endpoint WAJIB deklarasi `response_model` berbasis `api/schemas.py`; **dilarang return dict/objek mentah tanpa response_model** (nanti Decimal nekat jadi float diam-diam). Dummy-tag diekspos di API (`is_dummy`+`notice`) dan TIDAK boleh di-strip oleh consumer; dashboard Streamlit tetap wajib badge (RULES.md §3).

## Yang Perlu Direview Manual oleh Ghif (prioritas tinggi)
- Lihat RULES.md §4.
- **[SUDAH] BPS key sudah di-isi dan teruji** — tidak perlu aksi lagi darimu soal key.
- **Review hasil YoY BPS di dashboard** — verifikasi angka yang dirender masuk akal vs publikasi resmi BPS (contoh titik cek: Jan-2021 ≈ 1.55%, Des-2023 ≈ 2.61%).
- **Review hasil DJPPR di DB (Sesi 8, focus baru Sesi 14)** — verifikasi angka yield per seri vs keterangan pers resmi DJPPR. Contoh cek: FR0110 4-Agu-2026 ≈ 7.29574%, SPN01260905 ≈ 6.89% (Diskonto); terbaru 2023-2026: FR0101 12-Des-2023 ≈ 6.70988%, FR0109 16-Des-2025 ≈ 5.51372%. Query: `SELECT y.observation_date, b.code, y.yield_value FROM yield_observations y JOIN bonds b ON b.id=y.bond_id WHERE y.source='DJPPR' ORDER BY y.observation_date DESC LIMIT 20;`
- ~~**Keputusan backfill DJPPR penuh**~~ → **SELESAI (Sesi 14)**: 335 bonds, 1563 obs, 2015-05-26..2026-08-04 kontinu. Aksi lanjutan: fetch berkala (scheduler) untuk 2026 Sep–Des dst.
- **Keputusan cakupan historis BPS**: data baru sampai Des 2023 (API belum buka 2024-2025). Kukup (masih berfungsi sebagai fondasi) atau tunggu/pantau BPS buka tahun baru sebelum lanjut BI?
- ~~**KEPUTUSAN RISET BI (Sesi 15)**~~ → **SELESAI (Sesi 16):** fetcher BI ditulis & backfill PENUH: BI7DRR 126 obs (2016-04-21..2026-07-22), JISDOR 3198 obs (2013-05-20..2026-08-07), keduanya source='BI', 0 gap, idempoten. Spot-check: JISDOR 2026-08-07=17.913 (sesuai), BI7DRR 22-Jul-2026=5.75%.
- **Review data BI di DB (Sesi 16)** — verifikasi angka vs publikasi resmi BI. Query: `SELECT indicator_type, observation_date, value FROM macro_indicators WHERE source='BI' ORDER BY indicator_type, observation_date;` Contoh titik cek: JISDOR 2026-08-07 ≈ 17.913, BI7DRR 2026-07-22 ≈ 5.75%, BI7DRR 2025-07-16 ≈ 5.25%.
- **Review API via /docs (Sesi 17) — WAJIB manual:** jalankan `uvicorn api.main:app --reload` lalu buka `http://127.0.0.1:8000/docs`. Cek (1) 5 endpoint kebaca: `/health`, `/api/yield-curve/current`, `/api/yield-curve/history`, `/api/macro/latest`, `/api/macro/{indicator_type}`; (2) angka Decimal TIDAK jadi float aneh di JSON — nilai seperti `"17913.0000"`, `"5.7500"`, `"7.2957"` harus tetap string presisi; (3) dummy seed tetap ada is_dummy=true + notice badge.
- **Review default CORS Sesi 17:** origin yang diizinkan default = localhost:8501/8000 + 127.0.0.1 (Streamlit dashboard). Kalau dashboard jalan di origin lain, set `OBLIQ_CORS_ORIGINS` (koma).
- **Review keputusan var BPS**: kita pakai `var_id=1709` (IHK 90 Kota basis 2018=100), BUKAN `var_id=2` yang disebut di riset awalmu — karena var 2 terbukti hanya 1979-2019. Konfirmasi ini diterima.

## Catatan Belajar Finance
> Istilah/konsep baru yang ditemukan sepanjang development, di luar yang sudah ada di PRD.md §1 — dicatat di sini dulu, dipindah ke PRD.md kalau sudah settled.
- Sesi 8: **Lelang SUN multi-tranche** — satu lelang bisa menawarkan beberapa seri sekaligus (SPN jangka pendek + FR benchmark panjang) dalam 1 tanggal; hasil per seri = Weighted Average Yield pemenang. **SPN = diskonto (tanpa kupon)**. **Bid-to-cover ratio** (penawaran vs dimenangkan) menandai kekuatan permintaan. Semua sudah masuk PRD.md §1.

---

## Log Sesi
> Tambahkan entry baru di sini SETIAP akhir sesi kerja. Format: tanggal — apa yang dikerjakan — apa yang masih pending — apa yang WAJIB direview Ghif duluan — konsep finance baru yang ditemukan (kalau ada).

### 2026-08-11 — Sesi 20 (git init + commit pertama — perlindungan secret aktif)
- Dikerjakan:
  1. **`git init`** di root project (sebelumnya folder BUKAN git repo — temuan Sesi 19). Repo sekarang aktif di `master`.
  2. **`.gitignore` diperiksa & diperkuat** — sudah benar mencakup `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`; **ditambah `.coverage` dan `.coverage.*`** (artefak coverage report di root dari audit Sesi 19). Cek file cache HTML/PDF scraping: **tidak ada** — ketiga fetcher (bps/bi/djppr) parse respons in-memory, tidak menyimpan HTML/PDF ke disk. Satu-satunya HTML disimpan = `tests/fixtures/djppr/*.html` + `tests/fixtures/bi/*.xlsx` yang merupakan fixture test SENGaja (dipakai test suite), jadi **dibukukan**, bukan di-ignore.
  3. **`git add .` → `git status` dicek dulu sebelum commit**: `.env` TIDAK muncul di staged files (hanya `.env.example` yang ter-stage); `.venv/`, `__pycache__/`, `.pytest_cache/`, `.coverage` juga tidak ada. Verifikasi keras via `git ls-files | grep .env` → hanya `.env.example`. ✓
  4. **Commit pertama** `7f2eea8` — pesan: `Fase 1 backend OBLIQ: pipeline kurva yield & makro (audited & stable)` (bukan "initial commit" generik): 69 files, 8,027 insertions (backend API + pipeline + migrasi + scheduler + fixtures + docs).
  5. **TIDAK ada remote / TIDAK push** — sesuai instruksi, keputusan push terpisah nanti.
  6. **Verifikasi akhir:** `git status` → `nothing to commit, working tree clean`; `.env` tetap tidak ter-track.
- Hasil keputusan: **rekomendasi Sesi 19 (git init) dieksekusi — perlindungan `.gitignore` untuk `.env` kini BENAR-BENAR aktif.** Seluruh codebase di Fase 1 ada di history commit pertama sebagai baseline aman.
- Pending:
  - Dashboard Streamlit (kurva yield, indikator makro, halaman belajar) + gap handling di dashboard.
  - (Opsional) buat remote GitHub & push — keputusan terpisah, bukan sesi ini.
  - BPS 2024+ saat API buka (pemantauan otomatis via scheduler).
- Wajib direview Ghif:
  - Konfirmasi langkah git benar (branch `master`, commit hash `7f2eea8`, .env aman).
  - Setuju lanjut build dashboard Streamlit sesi berikutnya?
- Konsep finance baru: tidak ada sesi ini (opsi teknis repo).
- Catatan jujur: warning CRLF (LF→CRLF) di commit pertama normal utk checkout di Windows; identitas git lokal = user.name `Medaka356`, user.email `ghifariakbar2006@gmail.com` (dipakai commit otomatis — sebaiknya dikonfirmasi Ghif). `.gitignore` memakai pola `.env` (hanya file root) — ini sengaja: `.env.example` ikut di-track karena berguna sebagai template, sedangkan `.env` (berisi secret) di-ignore.

### 2026-08-11 — Sesi 19 (audit & stabilisasi backend menyeluruh — Fase 1 backend: audited & stable)
- Dikerjakan (SESI AUDIT, bukan nambah fitur — per instruksi Ghif):
  1. **Audit test coverage** — installed pytest-cov (dev-only) utk angka objektif:
     - `tests/test_api.py` (14) → **api/ 96%** (hanya main.py exception-handler 500 + service branch kosong yg missed).
     - `tests/test_scheduler.py` (9) → **pipeline/scheduler.py 78%** (missed: handler exception di dalam job — gap/NO-AWARD path — dan branch error).
     - `tests/test_bps.py` (13) → transformers/bps.py **95%**, validators/bps.py **81%**, fetchers/bps.py **58%** (yang missed = jaringan: `_fetch_year` retry/timeout).
     - `tests/test_bi.py` (17) → transformers/bi.py **82%**, validators/bi.py **85%**, fetchers/bi.py **41%** (networking miss).
     - `tests/test_djppr.py` (31) → validators/djppr.py **88%**, transformers/djppr.py **96%**, fetchers/djppr.py **35%** (networking miss).
     - **Kesimpulan coverage: logika transform/validasi TERTUTUP BAIK (82–96%); yang rendah (35–58%) konsisten = lapisan HTTP fetcher (retry/backoff/timeout & path sukses terhadap server nyata).** Ini gap otomatis wajar utk pipeline yg butuh jaringan — tapi berarti: **kasus network-error/timeout/retry TIDAK punya test deterministik** (hanya teruji live saat server down). Run scripts (`pipeline/run_*.py`) 0% tapi itu orkestrasi tipis yg logikanya sudah diuji via scheduler/runner live — sengaja tidak di-unit-test (butuh stubbing berlebihan).
     - **Gap coverage yg layak dilaporkan (belum difix, menunggu keputusan):** (a) tidak ada test deterministik untuk retry-backoff fetcher (monkeypatch requests agar timeout) — LOW, karena live testing sudah membuktikan retry jalan (lihat Sesi 18: timeout BI auto-retry, dan Sesi 19 gap-test di bawah); (b) scheduler.py gap-handler internal (catch per halaman) tidak ter-cover unit — MEDIUM, kerap jadi sumber regresi; (c) tidak ada test utk `api/main.py` exception handler 500 -> MEDIUM-LOW.
  2. **Idempotency menyeluruh** — `python -m pipeline.run_scheduler --run-once` 3x berturut-turut (subprocess benih bersih; loop pertama gagal per subprocess karena env PYTHONPATH tidak diwariskan → WinError 10106, diulang dgn env benar):
     - Baseline → setelah run #1 → #2 → #3: **bonds 335 → 335 → 335 → 335; yield_observations 1563 → 1563 → 1563 → 1563; macro_indicators 3367 → 3367 → 3367 → 3367. TIDAK BERUBAH setelah run pertama.**
     - **Bukti UPSERT (bukan skip):** `fetched_at` pada tiap run BERGERAK maju (inflation_yoy 23:53:49 → 23:56:42 → 23:58:37; yield DJPPR 23:55:01 → 23:57:43 → 23:59:39; BI 23:56:03 → 23:58:07 → 23:59:44) — artinya tiap run benar-benar menulis ulang row yg sama, dan COUNT tetap ⇒ idempotency DI JALUR STORAGE, bukan karena job di-skip. ✓
  3. **Gap handling nyata (sengaja matikan DJPPR)** — `API_BASE_URL` DJPPR diarahkan ke `http://127.0.0.1:9` (tidak ada yg listen → ConnectionError nyata): 
     - (a) **job lain tetap jalan:** BPS ok=True + BI ok=True, freshness BI (bi_7drr & usd_idr) & BPS (inflation_yoy) semuanya ter-refresh 2026-08-11 di run yg sama; (b) **error ke-log jelas:** 3x warning retry backoff (3s → 6s → 12s) lalu `ERROR pipeline.scheduler: Job DJPPR gagal` + traceback DjpprFetchError lengkap; (c) **TIDAK ada fabrikasi:** yield_observations source=DJPPR tetap 1563 (0 baris baru, 0 row rusak); (d) **proses tidak crash total:** run iterator menyelesaikan semua job (2 sukses + 1 gagal tercatat), laporan setiap job tetap keluar → scheduler yg dipakai production (daemon) juga aman karena tiap job punya try/except di `pipeline/scheduler.py`. ✓ (Catatan: `run_jobs_once` mengembalikan `ok=False` utk job gagal; CLI `--run-once` akan exit(1) bila ada job gagal — itu perilaku yang dirancang, bukan crash.)
  4. **Cross-check integritas lintas tabel** (query langsung ke DB):
     - **0 orphan** yield_observations.bond_id (semua JOIN ke bonds.bonds.id ada).
     - **0 tanggal aneh:** yield_observations & macro_indicators semuanya dalam 2000-01-01..hari ini (tidak ada 1970/future/masa depan); bonds maturity wajar (0 < 2010).
     - **0 duplikat ter-agregat:** tak ada grup (bond_id, observation_date) >1 dan tak ada grup (type, date) >1.
     - **Unique constraint beneran bekerja di level DB:** insert manual duplikat `bonds.code`, `(bond_id, observation_date)`, `(indicator_type, observation_date)` → **ketiganya REJECTED** (psycopg IntegrityError: uq_bonds_code / uq_yield_bond_date / uq_macro_type_date) dalam transaksi rollback — tidak merusak data. ✓
     - **Kewajaran numerik:** yield min/max = 1.9907% / 9.3432% (masuk akal utk SUN; di luar [0,40] = 0 row); 0 SPN punya coupon (konsisten zero-coupon); semua bond type='government' (335) + sources hanya {DJPPR}/{BI, BPS, DUMMY_CONTOH}. ✓
  5. **Full test suite** — `pytest -q --durations=10` → **84 passed dalam 1.23s**; test ter-lambat hanya 0.04s (parse XLSX fixture). Waktu total stabilize ~1-2s, tidak ada sinyal performance problem jangka pendek. (Satu StarletteDeprecationWarning soal `httpx` di `starlette.testclient` — kekhawatiran low di Fase 1.)
  6. **Cek .env/secrets** — **TIDAK ada commit apapun: folder ini BUKAN git repository (tidak ada `.git/`)**. `.gitignore` sudah benar (`.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`). `.env.example` hanya placeholder (`GANTI_PASSWORD`, `BPS_API_KEY=` kosong); `.env` beneran (berisi DSN + BPS key) TIDAK ada di path git manapun; **scan literal high-entropy (regex 32-hex / `sk-*/` / email+@) di semua .py/.md/.txt/.ini/.toml di luar .venv → 0 temuan**; kode hanya baca dari `os.getenv` (bps.py `_get_api_key`, connection.py `DATABASE_URL`), tidak ada key hardcoded. `.env` cuma 1 file di root + `.env.example`. ✓ — CATATAN: karena belum ada git, "lintas commit" tidak bisa diverifikasi; sebelum dashboard dilanjutkan sebaiknya `git init` dibuat supaya perlindungan `.gitignore` benar-benar aktif (rekomendasi, bukan bug).
- Hasil keputusan: **tidak ada bug fungsional yang ditemukan pada jalur data.** Semua poin aman. Gap yang tercatat = coverage test otomatis (bukan bug): retry/timeout fetcher deterministik + scheduler catch-path internal + API 500 handler — masing2 LOW/MEDIUM, tidak menghalangi lanjut dashboard.
- Pending:
  - Dashboard Streamlit (kurva yield, indikator makro, halaman belajar) + gap handling di dashboard.
  - (Opsional, sebelum lanjut) git init + commit pertama supaya perlindungan secret aktif.
  - BPS 2024+ saat API buka (pemantauan otomatis via scheduler).
- Wajib direview Ghif:
  - **Konfirmasi hasil audit diterima sebagai "Fase 1 backend: audited & stable".**
  - Setuju lanjut build dashboard Streamlit sesi berikutnya?
  - Setuju rekomendasi `git init` (kalau belum mau, minimal jangan pernah `git add .` tanpa cek .gitignore).
- Konsep finance baru: tidak ada sesi ini (murni audit).
- Catatan jujur: gap-handling simulasi memakai port mati (bukan memutus DNS/network sungguhan) tapi ini memicu ConnectionError nyata yang sama dengan server down; idempotency diuji lewat subprocess terpisah (bukan dalam-proses) sehingga engine/transaction benar-benar fresh tiap run; coverage report menyertakan pipeline seluruhnya tapi hanya untuk test suite lokal (DB lokal ikut terpakai oleh test_api, skip kalau DB mati).

### 2026-08-10 — Sesi 18 (scheduler APScheduler — pipeline jalan otomatis)
- Dikerjakan:
  - **APScheduler ditambahkan di requirements (≥3.10, instal 3.11.3) — sesuai rekomendasi ARCHITECTURE.md §2.**
  - `pipeline/scheduler.py` — orkestrasi fetch otomatis:
    - Setiap job = pipeline lengkap fetch→validate→transform→store untuk 1 sumber (ARCHITECTURE.md §4), mengembalikan laporan dict (`ok`, jumlah, `gaps`/`skips`).
    - **Kontrak gap: satu halaman/export yang gagal → tercatat di `gaps` (log + laporan), TIDAK membatalkan job; satu job gagal → `ok=False` + `error`, job lain tetap jalan** (SYSTEM.md 3: no silent gaps, satu sumber tidak membatalkan batch).
    - **Jadwal diesuaikan ritme sumber** (di `JOB_TRIGGERS`, satu sumber kebenaran): BPS = cron tgl-5 07:00 (BPS terbit CPI bulanan; sekaligus deteksi tahun baru dibuka di var 1709), DJPPR = Senin 06:30 dengan window 45 hari (lelang ~tiap 2 minggu), BI = harian 06:00 (JISDOR harian; BI7DRR window 90 hari menutupi siklus RDG).
    - Window `rolling` (bukan full re-fetch) utk DJPPR/BI karena sumbernya wajib range — idempotent upsert membuat pengulangan di tanggal sama = update, bukan dobel (ARCHITECTURE.md §4).
  - `pipeline/run_scheduler.py` — CLI: `--run-once` (jalan-kan semua/subset job lalu exit), `--jobs a,b`, tanpa arg = daemon (BackgroundScheduler, bertahan sampai Ctrl+C, tampilkan jadwal awal).
  - `pipeline/fetchers/bps.py` — `fetch(years: list[int] | None = None)`: dukung rangka kecil; tahun yang tidak didukung API di-skip (uang 2024 belum dibuka tapi request `[2024]` tidak error); `__main__` terima arg CLI tahun. (Default tetap semua tahun serve.)
  - **Teruji: 84 test hijau** (+3 BPS fetch range selection, +10 scheduler: build 1 job/sumber + trigger + max_instances, subset jobs, job tak dikenal dilewati, laporan bps/djppr/bi, BI structure-drift → gaps bukan crash, satu job gagal tidak menghentikan lain).
  - **VERIFIKASI LIVE `--run-once` (semua 3 sumber):** BPS → 4 tahun fetch, 36 YoY upsert; DJPPR → window 26-Jun..10-Agu, 3 lelang, 14 bonds, 25 obs (2 seri "-" skip wajar, 0 gap); BI → 2 export valid (bi_7drr 4 baris, usd_idr 32) termasuk **JISDOR 2026-08-10 yang baru** → usd_idr DB jadi 3199. 1 timeout transient saat fetch BI → retry 3s backoff sukses (bukti retry jalan).
  - **Idempotensi teruji:** DJPPR tetap 1563 obs (tidak dobel), BI macro tetap 3325 (126 bi_7drr + 3199 usd_idr), BPS tetap 36 (42 di kelompok inflasi_yoy karena +6 DUMMY_CONTOH yang memang sudah ada). Daemon mode: mulai + add_job + stop bersih.
- Pending:
  - Jalankan daemon sebagai proses tahan lama (cron OS / Task Scheduler / VPS) — keputusan deployment diperlambat sesuai ARCHITECTURE.md §6.
  - Dashboard Streamlit halaman kurva yield + indikator makro (belum ada sesi ini).
  - Rate-limit/auth API (sengaja, Fase 4). BPS perpanjang ke 2024+ saat API buka.
- Wajib direview Ghif:
  - **Setuju jadwal scheduler?** BPS bulanan (tgl-5 07:00), DJPPR mingguan (Senin 06:30), BI harian (06:00) — semua waktu lokal.
  - Setuju window rolling (DJPPR 45 hari, BI7DRR 90 hari, JISDOR 45 hari) + idempotent upsert sebagai strategi?
  - Spot-check hasil run-once di DB tetap wajar (contoh: JISDOR 2026-08-10 ≈ 17.9xx).
- Konsep finance baru: tidak ada sesi ini (murni infrastruktur scheduling).
- Catatan jujur: daemon diuji mulai/berhenti bersih (bukan dibiarkan jalan lama); run-once live murni sinkron dan berhasil semua job; test scheduler memakai stub bersih tanpa network/DB.

### 2026-08-10 — Sesi 17 (API FastAPI read-only — layer aplikasi mulai jalan, baca dari DB)
- Dikerjakan:
  - **Sesuai ARCHITECTURE.md §1 & §3:** API baca dari database (tidak pernah fetch sumber eksternal). Struktur baru `api/`:
    - `api/schemas.py` — response models; **Decimal di-serialisasi ke string presisi eksplisit** via `@field_serializer` (`"17913.0000"`, bukan float) — SYSTEM.md §1 poin 5; `DUMMY_BADGE` = teks badge RULES.md §3.
    - `api/dependencies.py` — `get_db` (session per request, di-close di finally); **router TIDAK akses session langsung** — pola router→service→db (NusaPath: handler→service→repo, di sini wujudnya router→service→query).
    - `api/services/yield_service.py` — `build_current_curve` (yield TERBARU per bond aktif, subquery max(observation_date), sort tenor asc; `as_of` = tanggal observasi terkini) + `build_bond_history` (rentang opsional, sort tanggal asc, beda status `not_found` vs `empty`).
    - `api/services/macro_service.py` — `build_macro_history` + `build_macro_latest` (snapshot max-date per indicator_type). **Honesty signal dummy tidak hilang di layer API:** tiap item punya `is_dummy` (source kosong/DI-DUMMY/prefix "DUMMY") + `notice` = teks badge saat dummy; RULES.md §3 tetap berlaku end-to-end.
    - `api/routers/yield_curve.py` — `GET /api/yield-curve/current`, `GET /api/yield-curve/history?bond_code=&start=&end=`.
    - `api/routers/macro.py` — `GET /api/macro/latest`, `GET /api/macro/{indicator_type}?start=&end=`.
    - `api/main.py` — FastAPI app, CORS (origin default localhost:8501/8000 + saat env `OBLIQ_CORS_ORIGINS`), `/health` (liveness + cek DB connect), exception handler 500 dengan detail jelas (bedakan dari 200-empty).
  - **Setiap item WAJIB bawa audit trail** (SYSTEM.md §1 poin 2-3): `source` + `fetched_at` + `observation_date` ada di semua item response.
  - **Error vs empty dibedakan:** data kosong → HTTP 200 `status="empty"` + `message` jelas (bukan silent empty array); rentang `start > end` → HTTP 422; bond tidak dikenal → `status="not_found"`; error internal tak terduga → HTTP 500 + log.
  - `db/connection.py`: engine di-`cache` (module-level `_engine`) — sebelumnya membuat engine baru tiap panggil (boros pool utk server yang hidup lama).
  - requirements.txt: + `fastapi`, `uvicorn`, `httpx` (TestClient).
  - **tests/test_api.py (14 test):** health; current curve (shape, sort tenor, audit field); history bond nyata (FR0100) + empty-range + not_found + invalid range 422; macro history + dummy flag (2026 = DUMMY_CONTOH, ter-tag true + notice) + empty + 422; latest snapshot ≥3 indikator + dummy flag inflation_yoy; unit Decimal→string. Test API skip bila DB unreachable (suite pipeline tetap bisa jalan di mesin tanpa Postgres).
  - **VERIFIKASI LIVE:** `uvicorn api.main:app` → `/health` 200 `database:ok`; `/docs` 200; `/openapi.json` menampilkan **5 path** (current, history, latest, {indicator_type}, health); curl: macro/latest = 3 indikator semua value **String** (`5.7500`, `17913.0000`); yield-curve/current = 335 poin, as_of 2026-08-04, tenor & yield string; history FR0100 = 23 obs ascending; empty + 422 + not_found terverifikasi. Em-dash notice dikonfirmasi UTF-8 benar di payload (tampilan console doang yang mojibake).
- Pending:
  - Review manual Ghif (`/docs`, 1-2 endpoint, Decimal tetap string) — prasyarat sebelum dashboard Streamlit dikoneksikan ke API.
  - Belum ada auth/rate-limit (sengaja, Fase 4); belum ada endpoint bonds metadata terpisah (kurva current sudah bawa info bond).
  - Scheduler APScheduler agar kolom data berjalan (2026 Sep–Des dst, BPS buka 2024-2025) otomatis masuk DB, lalu dashboard Streamlit halaman kurva.
- Wajib direview Ghif:
  - **Buka `/docs` sendiri** (`uvicorn api.main:app --reload` → `http://127.0.0.1:8000/docs`) — pastikan 5 endpoint terlihat & coba `Try it out`.
  - Cek JSON response: nilai Decimal tetap string presisi, bukan float (`"17913.0000"`, `"5.7500"`, `"7.2957"`).
  - Konfirmasi CORS default (localhost Streamlit) cukup untuk dashboard.
- Konsep finance baru: tidak ada sesi ini (murni layer API). Satu catatan perilaku: kurva current = yield lelang **terbaru per seri** (berita lelang 2-mingguan), bukan yield pasar harian sekunder — konsisten dengan data sumber (DJPPR = hasil lelang), jangan diinterpretasi sebagai mark-to-market harian.
- Catatan jujur: test API integration terhadap DB lokal yang sudah ada datanya (skip bila DB mati); verifikasi `/docs` via server live uvicorn sukses; belum di-host, belum di-autentikasi, dan belum diverifikasi GHIF secara visual di browser.

### 2026-08-10 — Sesi 16 (fetcher BI + backfill penuh BI7DRR & JISDOR)
- Dikerjakan:
  - **Pending sesi 15 di-approve Ghif & dikerjakan: pipeline BI lengkap** (pola GET hidden fields → POST Unduh → XLSX → parse stdlib):
    - `pipeline/fetchers/bi.py` — `fetch_bi7drr` (1 request full, tanggal start default 2016-04-21) & `fetch_jisdor` (per tahun via `run_bi_fetch --jisdor-years`); retry 3x + backoff 3s doubling, timeout 30s, sleep sopan 1s antar tahun; `BiExport` dataclass.
    - `pipeline/validators/bi.py` — `validate_xlsx` parse XLSX tanpa openpyxl (zipfile + ElementTree + sharedStrings), header `NO|Tanggal|{Kurs|BI-7Day-RR}` → `BiStructureError` kalau layout berubah (pola DjpprStructureError: berhenti eksplisit, jangan parse salah diam-diam). Pydantic `BiRow`/`BiSpreadsheet`.
    - `pipeline/transformers/bi.py` — `"4.75 %"`→Decimal 4.75 (koma desimal juga OK), kurs integer `17913`→Decimal, tanggal US serial `8/7/2026 12:00:00 AM` (M/D/Y — 8/7 = 7 Agu) dan Indonesia `15 Desember 2016` → `date`; sort ascending `(indicator_type, observation_date)`; `MacroIndicatorRecord` source='BI'.
    - `pipeline/storage/bi.py` — upsert idempotent `ON CONFLICT (indicator_type, observation_date)`; `indicator_type` = `bi_7drr` / `usd_idr` (sesuai SCHEMA.md).
    - `pipeline/run_bi_fetch.py` — CLI `--bi7drr` dan `--jisdor-years Y1,Y2,...`; checkpoint per tahun; laporan akhir + GAP.
  - **Fixture + test:** `tests/fixtures/bi/bi7drr_2016_sample.xlsx` (3118 B, 9 baris nyata) & `jisdor_full_sample.xlsx` (71597 B, 3198 baris nyata dari Sesi 15); `tests/test_bi.py` (17 test). **58 test hijau** (3 test di-fix di sesi ini: transform sort ascending → assertions cek `records[0]`=paling awal, `records[-1]`=paling baru).
  - **BACKFILL PENUH (teruji live):** `--bi7drr` → **126 obs** (2016-04-21..2026-07-22); `--jisdor-years 2016,2020,2026` (validasi checkpoint 3 tahun) lalu `--jisdor-years 2013,2014,2015,2017,2018,2019,2021,2022,2023,2024,2025` → **3198 obs** (2013-05-20..2026-08-07). **0 gap, 0 duplicate**, tiap bulan kalender Mei-2013..Agu-2026 punya data. 1 timeout transient saat 11-year batch → auto-retry sukses (bukti retry bekerja).
  - **Idempotensi teruji:** re-run `--bi7drr --jisdor-years 2016` → upsert 372 baris sama, DB tetap 126 + 3198 (tidak dobel).
- Pending:
  - **Review Ghif atas data BI** (spot-check vs publikasi BI) sebelum dianggap final.
  - JISDOR raw export tahunan tidak disimpan permanen (hanya diproses); kalau mau arsip, perlu langkah simpan file tambahan.
  - Fetcher BPS perpanjang ke 2024+ (nanti BPS buka), scheduler APScheduler, API FastAPI, dashboard kurva yield + halaman makro.
  - 2026 Sep–Des (data berjalan) masuk via fetch berkala.
- Wajib direview Ghif:
  - **Spot-check data BI vs publikasi resmi** (contoh titik cek: JISDOR 2026-08-07 ≈ 17.913, BI7DRR 2026-07-22 ≈ 5.75%, BI7DRR 2025-07-16 ≈ 5.25%). Query: `SELECT indicator_type, observation_date, value FROM macro_indicators WHERE source='BI' ORDER BY indicator_type, observation_date;`
  - Konfirmasi scope backfill BI sesuai harapan (BI7DRR 126 obs sejak 2016; JISDOR ~3.1k obs sejak 2013) — tidak dibackfill lebih tua karena sumber memang tak punya data sebelum 2013-05-20 / 2016-04-21.
- Konsep finance baru: **reverse repo** — BI7DRR adalah suku bunga acuan BI (reverse repo 7-hari, peluncuran Apr 2016 menggantikan BI-Rate). Sudah cukup tercatat Sesi 15; tidak ada tambahan sesi ini.
- Catatan jujur: data XLSX di-fetch & di-parse dari byte langsung (tidak menyimpan arsip xlsx per tahun ke disk); verifikasi kontinuitas lewat query bulan-kalender (160 bulan tervalidasi). Nilai belum di-cross-check ke publikasi BI oleh manusia (prasyarat review Ghif).

### 2026-08-10 — Sesi 15 (riset BI live: BI7DRR + JISDOR — akses & format TERBUKTI MUDAH)
- Dikerjakan:
  - **`dataapi.bi.go.id/dataexchange/v1` (yang disebut riset GitHub) → DNS TIDAK resolve** (getaddrinfo Errno 11001) — jalur API portal itu mati, tidak dipakai.
  - Inspeksi `www.bi.go.id` (SharePoint/ASP.NET WebForms: `__VIEWSTATE`, `__EVENTVALIDATION`, `aspnetForm`, `_spPageContextInfo`) — **data tabel render server-side di HTML awal** (headless browser TIDAK diperlukan). Raw HTML disimpan ke temp `bi_raw/` (jisdor_id/en, bi7drr_id/en, jisdor_tx_id).
  - **JISDOR** (`/id/statistik/informasi-kurs/jisdor/default.aspx`, WebPart `ctl00_ctl54_g_f51e6b6d...`): filter "Dari/Sampai" (`TextBoxFrom`+`HiddenFieldDateFrom`, `TextBoxDateTo`+`HiddenFieldDateTo`, format `dd/mm/yyyy`) + tombol **"Unduh"** (`ButtonExport`, `btn-export`). POST dengan hidden fields + rentang + `ButtonExport=Unduh` → **XLSX asli** (`Informasi Kurs Jisdor.xlsx`, 71.6KB). Kolom `NO|Tanggal|Kurs`; Kurs integer Rupiah (`17913`); tanggal serial US (`8/7/2026 12:00:00 AM`).
  - **BI7DRR** (`/id/statistik/indikator/bi-rate.aspx`, WebPart `ctl00_ctl54_g_78f62327...`): filter `TextBoxDateStart`/`TextBoxDateEnd` + **`ButtonExport`** → **XLSX** (`BI-7Day-RR.xlsx`). Kolom `NO|Tanggal|BI-7Day-RR`; nilai `4.75 %` (dengan spasi); tanggal "22 Juli 2026". Ada juga kolom `Pranala Siaran Pers` di HTML tapi export cukup 3 kolom.
  - **Filter periode benar-benar berlaku di export** (narrow range = baris sesuai): JISDOR 2016 penuh = 246 baris, 2020-2021 BI7DRR = 24 baris, 2016 BI7DRR = 9 baris. Total JISDOR 2010-2026 = **3198 baris** (mulai 2013-05-20 → ada cap ~3200 baris export; fetch per-tahun lebih aman). BI7DRR penuh = **126 baris** (2016-04-21 s.d. 2026-07-22; 2000-2012 = XLSX kosong, konsisten dgn peluncuran BI7DRR 2016).
  - **Parse XLSX tanpa openpyxl** (belum terpasang): stdlib `zipfile` + `xml.etree.ElementTree` + sharedStrings inline — berhasil baca header & 3198 baris. Tidak perlu tambah dependency.
  - `robots.txt` bi.go.id = `Allow: /` (hanya disallow `/_layouts`, `/Style Library`, dst) — halaman statistik boleh di-crawl; rate-limit sopan tetap wajib.
  - PROGRESS.md: ringkasan riset BI di-update (hapus duplikasi), status head, checklist Fase 0, "Diketahui Bermasalah", "Yang Perlu Direview".
- Pending:
  - **Tulis fetcher BI** (`pipeline/fetchers/bi.py` + validator + transformer + storage + runner) — menunggu approval Ghif.
  - Jangkauan awal yang disarankan: BI7DRR full (1 request) + JISDOR per-tahun 2013-2026 (~14 request, ~3.1k obs).
  - Scheduler, API, dashboard kurva yield.
- Wajib direview Ghif:
  - **Setuju pendekatan export XLSX via POST WebForms (bukan scrape HTML/pagination)?**
  - **Setuju jangkauan backfill BI?** (BI7DRR 2016-04-21..now = 126 obs; JISDOR 2013-05-20..now = ~3.1k obs) atau cakupan lain.
  - Konfirmasi spot-check nilai (contoh: JISDOR 2026-08-07=17.913, BI7DRR 22-Jul-2026=5.75%).
- Konsep finance baru: **BI7DRR (BI 7-Day Reverse Repo Rate)** adalah suku bunga acuan BI sejak April 2016 (menggantikan BI-Rate) — cocok dengan indikator `bi_7drr` di SCHEMA.md; **JISDOR** = kurs acuan USD/IDR harian — cocok dengan `usd_idr`.
- Catatan jujur: parse XLSX diuji via stdlib ad-hoc; belum ada validator/transform resmi. Halaman "Kurs Transaksi BI" (`jisdor_tx_id.html`) di-save tapi BELUM dieksplorasi (tidak wajib untuk indikator ini — JISDOR sudah cukup).

### 2026-08-10 — Sesi 14 (backfill DJPPR 2023-2026 — backfill PENUH SELESAI)
- Dikerjakan:
  - Menutup gap Jan 2023–Mei 2026 secara berurutan (pola checkpoint per rentang yang sudah terbukti):
    - `--start 2023-01-01 --end 2023-12-31` → **27 halaman, 27 valid, 0 gap** → 24 tanggal lelang 2023, 153 obs (42 bonds dalam batch).
    - `--start 2024-01-01 --end 2024-12-31` → **24/24 valid, 0 gap** → 24 lelang, 156 obs (32 bonds).
    - `--start 2025-01-01 --end 2025-12-31` → **24/24 valid, 0 gap** → 24 lelang, 177 obs (30 bonds).
    - `--start 2026-01-01 --end 2026-05-31` → **10/10 valid, 0 gap** → 10 lelang, 87 obs (29 bonds) — nyambung mulus ke 2026 Jun–Agu dari Sesi 8 (5 lelang/42 obs).
  - **Tanpa DjpprStructureError baru** di semua rentang (pola approved — Nopember, kode seri terbelah, label kupon pendek, DjpprNoAward — semua sudah jalan); seri "-" (tak dimenangkan) di-skip dengan log, terbanyak 2025 (19 seri "-" di berbagai lelang).
  - **Bonus recover (auto):** 3 slug SPN tanpa tanggal (page 3976/3968/3891, fallback DPublishedID 13-Jan-2023 masuk window 2023) ternyata berisi lelang **2015**, bukan 2016: 2015-05-26 (SPN12160304, FR0068, FR0070), 2015-10-13 (FR0053/56/72, SPN03160115, SPN12161015), 2015-10-27 (FR0053/56/67/73, SPN12160708) → **rentang awal DJPPR mundur dari 2015-11-10 ke 2015-05-26**. Dugaan Sesi 11 bahwa 2015 cuma 3 lelang keliru karena slug-scan hanya melihat halaman ber-slug-tanggal; 3 halaman SPN-slug ini ternyata lelang 2015 (bersama page 3554 yang sudah recover 2016-01-05 di Sesi 13).
  - **VERIFIKASI KONTINUITAS:** per bulan Jan 2023 – Mei 2026 semuanya punya ≥1 lelang (1-3 tgl per bulan, ritme 2-mingguan + kadang sambungan); **TIDAK ADA bulan kosong**. Final DB: **335 bonds, 1563 yield_observations, 2015-05-26 s.d. 2026-08-04**.
  - 41 test tetap hijau (tidak ada perubahan kode sesi ini — hanya run + verifikasi).
  - PROGRESS.md: gap 2023-2026 ditandai RESOLVED, checklist per-tahun = selesai, status head di-update ke "backfill DJPPR PENUH SELESAI".
- Pending:
  - Backfill DJPPR SELESAI. Yang tersisa untuk Fase 1: **fetcher BI (BI7DRR + kurs JISDOR/USD-IDR)** — prioritas berikutnya; scheduler APScheduler (fetch berkala agar 2026 Sep–Des masuk otomatis); API FastAPI; dashboard kurva yield.
  - BPS: pantau var 1709 buka 2024 (API masih s.d. 2023).
- Wajib direview Ghif:
  - Konfirmasi angka per rentang (spot-check vs keterangan pers): 2023-12-12 FR0101≈6.70988%, 2024-12-10 FR0104≈6.86962%, 2025-12-16 FR0109≈5.51372%, 2026-05-26 FR0109≈6.66981%.
  - Validasi recover 2015 baru (FR0068/FR0070 26-Mei-2015, FR0067 27-Okt-2015) vs publikasi.
  - Setuju lanjut ke fetcher BI setelah ini.
- Konsep finance baru: tidak ada sesi ini (murni backfill + verifikasi).

### 2026-08-10 — Sesi 13 (backfill DJPPR 2017–2022 + fix no-award)
- Dikerjakan:
  - Diagnosa lengkap lelang 08-Mei-2018 (PageId 3146) yang gagal di Sesi 12: dump raw @Konten (8253 byte) vs kontrol 24-Apr-2018 (10704 byte, parse OK) → **BUKAN quirk struktur**; Pemerintah memutuskan "tidak menerima semua penawaran" (yield yang masuk "di luar kewajaran") → lelang DIBATALKAN total, memang tidak ada tabel hasil.
  - Implementasi sesuai approval: `DjpprNoAwardError(DjpprStructureError)` + guard frasa `_NO_AWARD_RE` (`tidak menerima semua penawaran` / `menolak semua/seluruh penawaran`) SEBELUM parse tabel di `validate_page`. Runner menangkap `DjpprNoAwardError` terpisah → dilaporkan sebagai "Lelang dibatalkan: N (skip terdokumentasi)", bukan GAP.
  - Fixture `tests/fixtures/djppr/konten_2018_05_08_noaward.html` + `TestNoAwardSkip` (3 test: error khusus, subclass StructureError, tidak menimpa halaman normal). **Full suite: 41 pass.**
  - Backfill bertahap bersih:
    - 2017: 23 lelang, 39 bonds, 117 obs, 0 gap (tidak ada perubahan kode — struktur 2017 sama dgn 2016/2015).
    - 2018: 22 valid + **1 skip terdokumentasi** (08-Mei), 40 bonds, 118 obs, 0 hard gap.
    - 2019: 21 lelang, 40 bonds, 142 obs, 0 gap.
    - 2020: 25 lelang, 37 bonds, 165 obs, 0 gap.
    - 2022: 29 halaman (27 tanggal unik, ritme 2-mingguan), 47 bonds (2022-only), 177 obs, 0 gap; termasuk halaman tanggal-ganda & seri sukuk `FRSDG001` (25-Okt & 22-Nov-2022).
  - **Efek bonus:** halaman SPN-slug 2016 page 3554 (DPublishedID fallback 22-Des-2022 → masuk window 2022) ter-fetch, @Tanggal asli 2016-01-05 → 5 obs 2016 terisi (FR0053/56/72, SPN12160401, SPN12170106). Sebelumnya tercatat gap (Sesi 11).
  - **TEMUAN BERAT:** 2023..2025 (Jan 2023–Mei 2026) BELUM pernah di-backfill — Sesi 8 hanya Jun-Agu 2026, checklist 2017-2020/2022 melupakan 2023-2025. Gap kurva 3,5 tahun. Lari 2023 akan sekaligus auto-recover 3 slug SPN-2016 tersisa (page_id 3976/3968/3891, DPublishedID 13-Jan-2023).
  - Total DB DJPPR: 248 bonds, 977 obs, rentang 2015-11-10 .. 2026-08-04.
  - PROGRESS status head / checklist / keputusan teknis / bermasalah di-update.
- Pending:
  - **KEPUTUSAN Ghif akhir sesi: STOP — 2023..2025 (Jan 2023–Mei 2026) dibiarkan sebagai gap terdokumentasi.** Backfill DJPPR dianggap selesai. Gap wajib tampil jelas di dashboard.
  - 2026 sisanya (Sep-Des) belum di-backfill (Sesi 8 hanya Jun-Agu).
  - Fetcher BI, scheduler, API, dashboard kurva yield.
- Wajib direview Ghif:
  - Approve penanganan no-award (`DjpprNoAwardError` + skip terdokumentasi).
  - Konfirmasi angka: FR0077 21-Nov-2018 ~7.94539%, FR0081 19-Nov-2019 ~6.46570%, FR0086 1-Des-2020 ~5.06768%, FR0095 6-Des-2022 ~6.51761%.
  - Cek seri `FRSDG001` (sukuk) pada 2022 — kode SUN non-FR/SPN, memvalidasi regex `_CODE_RE`? (Kode lolos `[A-Z]{2,6}\d{2,8}`.)
- Konsep finance baru: **lelang dibatalkan total (no award)** — Pemerintah boleh menolak semua penawaran; hasil lelang hari itu memang kosong, bukan gap parsing.

### 2026-08-10 — Sesi 12 (backfill DJPPR 2016)
- Dikerjakan:
  - Backfill **2016 solo** (checkpoint per tahun): `--start 2016-01-01 --end 2016-12-31` → **21 halaman fetch, 21 valid, 0 gap struktur** → 29 bonds unik, 95 yield_observations (source='DJPPR').
  - Verifikasi DB: 21 tanggal lelang (19-Jan s.d. 6-Des 2016), per lelang 4–5 obs.
  - 4 slug SPN tanpa tanggal lelang (sesuai keputusan Ghif): **di-skip dengan log warning eksplisit** (page_id 3976, 3968, 3891, 3554 — `spn12160708(reopening)` dkk), fallback DPublishedID (13-Jan-2023 / 22-Des-2022) di luar rentang → TIDAK di-fetch paksa, bukan gap tersembunyi.
  - 3 seri "-" (tak dimenangkan, yield '-') di-skip dengan log double (validator+transformer): FR0072 6-Des-2016, FR0073 13-Sep-2016, SPN12170804 30-Agu-2016.
  - Tanpa DjpprStructureError baru; TIDAK ada perubahan kode. 38 test tetap hijau.
- Pending:
  - **STOP setelah 2016 — menunggu approval Ghif utk lanjut 2017.**
  - 2017, 2018, 2019, 2020, 2022 belum di-backfill.
  - Fetcher BI, scheduler, API, dashboard kurva yield.
- Wajib direview Ghif:
  - Approve lanjut 2017.
  - Konfirmasi angka 2016 (contoh: FR0073 25-Okt-2016 ~7.40879%, SPN12170804 25-Okt-2016 ~5.99421%).
- Konsep finance baru: tidak ada sesi ini.

### 2026-08-10 — Sesi 11 (verifikasi rentang awal DJPPR + backfill 2015)
- Dikerjakan:
  - **VERIFIKASI rentang awal (bukan asumsi):** fetch full listing (270 baris total, 260 auction), parse semua slug date → data paling awal yang BENAR-BENAR tersedia = **2015-11-10** (3 lelang di 2015: 10-Nov, 24-Nov, 1-Des). Tidak ada lelang sebelum Nov 2015 di listing CMS.
  - Backfill **satu tahun paling awal saja** (sesuai instruksi): `--start 2015-01-01 --end 2015-12-31` → **3 halaman fetch, 3 valid, 0 gap** → 9 bonds unik, 13 yield_observations (source='DJPPR'). Verifikasi DB: 3 tanggal lelang (4+4+5 obs).
  - Temuan PENTING: 2015 ternyata memakai **struktur @Konten yang SAMA** dengan 2021/2023/2026 (label-keyed parser langsung jalan, tanpa quirk baru) — kekhawatiran "platform CMS berbeda utk 2015-2017" ternyata TIDAK muncul di 2015. Yield wajar utk era itu (FR0056 ~8.65%, SPN ~6–7%).
  - 38 test tetap hijau (tidak ada perubahan kode sesi ini — hanya verifikasi + run).
- Pending:
  - **STOP setelah 2015** — menunggu approval Ghif utk lanjut 2016, 2017, dst (checkpoint per tahun).
  - Tahun 2016 berikutnya punya 4 slug SPN TANPA tanggal lelang (page_id 3976/3968/3891/3554, era 2016, slug `spn...`) yang ke-skip oleh filter slug-date dengan fallback DPublishedID=migration (13 Jan 2023). Perlu dicek manual apakah 4 halaman itu cover lelang 2016 (potensi gap terlihat — dicatat, bukan gap tersembunyi).
  - 2016–2020 + 2022 belum di-backfill.
  - Fetcher BI, scheduler, API, dashboard kurva yield.
- Wajib direview Ghif:
  - **Approve lanjut 2016** dulu (jangan sekaligus 6 tahun).
  - Konfirmasi angka 2015 vs keterangan pers DJPPR (contoh: FR0056 10-Nov-2015 ~8.65374%, FR0073 24-Nov-2015 ~8.86981%).
  - Catatan utk 2016: 4 slug SPN tanpa tanggal lelang perlu keputusan handle (manual inspect vs dilewati dengan log).
- Konsep finance baru: tidak ada sesi ini.

### 2026-08-10 — Sesi 10 (backfill DJPPR 2021 + fix 3 quirk struktur)
- Dikerjakan:
  - Fix quirk struktur 2021 yang di-approve sesi 9 (3 pola, semuanya di `pipeline/validators/djppr.py`):
    1. **Nopember** — ejaan lama resmi "Nopember" untuk November di tanggal jatuh tempo → `_ID_MONTHS` + `"Nopember": 11` (alias "November").
    2. **Kode seri terbelah antar tag** — page 2021 menulis `<strong>FR00</strong><strong>86</strong>` → `_CODE_JOIN_RE` + `normalize_code()` (2 tempat: `_find_series_code_row` + ekstraksi `codes` di `validate_page`).
    3. **Label baris kupon pendek** ("Kupon", bukan "Tingkat kupon") pada greenshoe 2021 → `_LABEL_COUPON_ALIASES` + `_extract_row_by_label` menerima tuple alias.
  - Fixtures baru: `konten_2021_04_14_greenshoe_0.html`, `konten_2021_08_18_0.html`, `konten_2021_08_03_0.html` (+ class `TestParseLegacyQuirks2021` 5 test, termasuk `test_greenshoe_label_kupon_pendek_parsed`).
  - **Full test suite: 38 pass / 0 fail** (35 lama + 3 test oracle 2021).
  - **Backfill 2021 PENUH `--start 2021-04-01 --end 2021-12-31`: 15 halaman di-fetch, 15 valid, 0 gap** → 29 bonds unik, 103 yield_observations (source='DJPPR'), idempoten (re-run tidak dobel karena previous partial-run rows di-upsert). Verifikasi DB: 15 tanggal lelang 13-Apr s.d. 26-Okt 2021, 103 obs total.
- Pending:
  - JANGAN lanjut 2022 di sesi ini (menunggu review Ghif atas laporan 2021).
  - Backfill tahun lebih tua (2020, dst.) — juga menunggu keputusan scope.
  - Fetcher BI, scheduler, API, dashboard kurva yield.
- Wajib direview Ghif:
  - **Hasil parse 3 halaman yang tadinya gagal** (rincian di laporan sesi): greenshoe 14-Apr-2021 (5 seri FR, yield 5.74944–7.29968, kupon 5.5–7.5%), 18-Agu-2021 & 3-Agu-2021 (7 seri tiap lelang, SPN Diskonto + FR, jatuh tempo pakai "Nopember").
  - **Total 2021**: 15 lelang, 29 bonds, 103 yield_observations, 0 gap — sebelum lanjut 2022.
  - Konfirmasi angka vs keterangan pers resmi DJPPR (contoh: FR0086 14-Apr-2021 yield 5.74944%, maturity 15-Apr-2026).
- Konsep finance baru: tidak ada sesi ini (fix struktur data).

### 2026-08-10 — Sesi 9 (fix bug filter tanggal listing DJPPR)
- Dikerjakan:
  - **Bug: `--start 2021-04` balikin 0 halaman.** Akar: `fetch_listing` memfilter pakai `DPublishedID`, tapi page lelang PRA-CMS (≤2022) punya DPublishedID = tanggal MIGRASI CMS (Jul 2022–Jan 2023), BUKAN tanggal lelang. Auction date yang benar tertanam di slug URL (`hasillelang...tanggal27april2021`).
  - Fix di `pipeline/fetchers/djppr.py`: `_parse_slug_date()` (regex `{dd}{bulan}{yyyy}`, bulan Indonesia lowercase, handle "nopember"+kompleks slug), `DjpprListingItem.auction_date`, `fetch_listing` filter by slug-date + fallback DPublishedID + log warning untuk slug tanpa tanggal (4 halaman SPN tahun-tua, fallback ke DPublishedID). DROP early-break watermark lama (tidak valid karena interleave migrasi).
  - 6 test `TestSlugAuctionDate` di `tests/test_djppr.py` (slug nyata 2016/2019/2021/2026 + greenshoe + tanpa tanggal). 23 test hijau.
  - Verifikasi live: 2021-04..12 kini menemukan **15 halaman** (semua lelang 13-Apr..26-Okt 2021, DPublishedID semua = 5 Okt 2022 — bukti quirk migrasi).
  - Ditemukan **3 gap struktur** saat parse 2021 (dilaporkan & di-approve Ghif untuk fiks di Sesi 10).
- Pending:
  - Aplikasi 3 fix validator (Nopember, kode terbelah, label kupon pendek) → dikerjakan di Sesi 10.
  - Re-run 15 halaman, lalu backfill 2021 penuh.
- Wajib direview Ghif:
  - Approve 3 fix quirk struktur 2021.
  - Konfirmasi pergeseran "tahun pertama data" — listing ternyata membawa halaman s.d. 2015 (bukan Apr 2021 seperti catatan Sesi 7), TotalRecord=270 masih eksis.
- Konsep finance baru: tidak ada (bug data pipeline).

### 2026-08-10 — Sesi 8 (fetcher DJPPR end-to-end)
- Dikerjakan:
  - Model `issuers`/`bonds`/`yield_observations` di `db/models.py` + migration `a1b2c3d4e5f6` (`bonds.code` UNIQUE, `yield_observations` UNIQUE bond_id+observation_date). `alembic upgrade head` sukses di DB live.
  - `pipeline/fetchers/djppr.py`: listing `POST /page/filter` (paginasi, filter prefix UrlPath `hasillelangsuratutangnegara`, rentang tanggal dari DPublishedID "4 Aug 2026") + detail `GET /page?url=` per halaman; timeout+retry backoff; sleep sopan 1s.
  - `pipeline/validators/djppr.py`: parse `@Konten` HTML table pakai BeautifulSoup/lxml, **label-keyed (order-independent)**; `DjpprStructureError` kalau struktur berubah/mismatch kolom (RULES.md §1 — jangan parse salah diam-diam). Pydantic `DjpprAuction`/`DjpprSeries`.
  - `pipeline/transformers/djppr.py`: 1 lelang → banyak seri → 1 bond per kode + 1 yield_observations per (seri, tanggal); Decimal semua; seri "-" (tidak dimenangkan) di-skip; tenor_years = maturity − tanggal lelang; issue_date NULL (reopen tak disclose issue asli).
  - `pipeline/storage/djppr.py`: upsert bonds by code (RETURNING id, pakai row[0]), lalu yield_observations by (bond_id, observation_date) — keduanya idempoten.
  - `pipeline/run_djppr_fetch.py`: CLI `--months/--start/--end`, per-page gap reporting (tidak abort batch), laporan akhir.
  - Fixtures: `tests/fixtures/djppr/*.html` (3 sample nyata: 2026-08-04, 2023-12-12, 2026-07-21 dengan "-"). `tests/test_djppr.py` (17 test): parse 2 rentang tahun, reject struktur berubah, skip "-", transform 1-lelang-banyak-seri, seri sama di 2 lelang.
  - requirements.txt: + beautifulsoup4, lxml, pdfplumber.
  - PRD.md §1: + lelang, SPN, FR, bid-to-cover ratio.
  - **Teruji nyata**: `python -m pipeline.run_djppr_fetch --months 3` → rentang Jun 1–Agu 10 2026 = **5 lelang, 19 bonds, 42 yield_observations (source='DJPPR')**, 3 seri "-" di-skip, **0 gap**; re-run idempoten (tetap 19/42). Verifikasi DB: 5 tanggal lelang wajar (Jun 9, 23; Jul 7, 21; Agu 4 2026), SPN coupon NULL.
- Pending:
  - Backfill DJPPR penuh (270 halaman) — keputusan terpisah, `--start/--end`; pantau format green-shoe dan konsistensi lintas tahun.
  - Fetcher BI (BI7DRR, kurs USD/IDR) — sesi terpisah.
  - Scheduler, API FastAPI, dashboard kurva yield, gap-handling teruji.
- Wajib direview Ghif:
  - Verifikasi angka yield vs keterangan pers resmi (contoh cek FR0110 4-Agu-2026 ≈ 7.29574%, SPN01260905 ≈ 6.89%).
  - Keputusan backfill penuh vs mulai-now-bertahap.
  - Konfirmasi pendekatan HTML-in-JSON (bukan PDF parsing) diterima.
- Konsep finance baru: **lelang multi-tranche, SPN diskonto tanpa kupon, FR benchmark, bid-to-cover ratio** (masuk PRD.md §1).
- Catatan jujur: teruji pada 5 lelang nyata (3 seri "‑" ditangani). Yang BELUM: parse green-shoe/lelang non-regular, backfill historis, konsistensi format lelang pra-2020, BI.

### 2026-08-10 — Sesi 6 (fetcher BPS end-to-end + migration formal)
- Dikerjakan (satu checkpoint besar: "pastikan 1 sumber jalan dulu" per PROGRESS Fase 0):
  - Riset live API BPS: temuan penting — `var_id=2` cuma 1979-2019; IHK modern = `var_id=1709` (IHK 90 Kota, 2018=100) + `vervar=9999`; API tolak range `th` (harus per-tahun pakai th_id); datacontent key decode `{vervar}{var}{th_id:04d}{month}`; data cuma sampai 2023.
  - `db/models.py` (SQLAlchemy 2.0 `Mapped`) + setup Alembic (`alembic.ini`, `env.py`, `script.py.mako`) + migration `c33a23e70646` create `macro_indicators` (checkfirst, idempoten). `alembic upgrade head` sukses. **Keputusan: tabel dummy dipakai apa adanya** (struktur identik, tak perlu drop/alter).
  - `pipeline/fetchers/bps.py`, `pipeline/validators/bps.py`, `pipeline/transformers/bps.py`, `pipeline/storage/bps.py`, `pipeline/run_bps_fetch.py` sesuai kontrak ARCHITECTURE §4.
  - `pytest.ini` + `tests/test_bps.py` (10 test): decode key, logika YoY manual, validator tolak data salah bentuk.
  - Teruji nyata: `python -m pipeline.run_bps_fetch` → **4 tahun fetch, 36 YoY dihitung, 36 di-upsert (source='BPS')**; verifikasi psql: 36 baris BPS + 6 dummy; re-run idempoten (tetap 36). Nilai contoh nyata tersimpan: Jan-2021=1.5528%, Okt-2023=2.5632%, Des-2023=2.6147% (cocok publikasi resmi BPS).
  - requirements.txt: + pydantic, requests, alembic, pytest.
  - PRD.md §1: tambah konsep IHK, inflasi YoY vs MtM, kenapa Obliq hitung sendiri (SYSTEM.md §5 wajib).
- Pending:
  - Fetcher BPS perpanjang sampai tahun terbaru — nunggu BPS buka 2024/2025 di var 1709 (pantau; bukan bug).
  - Fetcher DJPPR & BI (belum tersentuh sesi ini — sengaja, sesuai instruksi "BPS dulu").
  - Scheduler APScheduler (Fase 1 masih manual).
- Wajib direview Ghif:
  - Konfirmasi keputusan `var_id=1709` (bukan var 2 dari riset awal — terbukti var 2 cuma 1979-2019).
  - Verifikasi visual dashboard: source BPS muncul tanpa badge; keterangan "data per Des 2023" jelas.
  - Cakupan historis: cukup s.d. 2023 atau tunggu BPS buka tahun baru?
- Konsep finance baru: **IHK, inflasi YoY vs MtM, dan alasan hitung YoY manual** (sudah masuk PRD.md §1).
- Catatan jujur: pipeline teruji dengan data API nyata & masuk DB. Yang BELUM dicoba: parsing PDF DJPPR, scraping BI, scheduling otomatis, tampilan dashboard lanjutan (halaman makro chart) — semua Fase 1 lanjutan.

### 2026-08-10 — Sesi 5 (listen_addresses lokalan + riset DJPPR/BI)
- Dikerjakan:
  - `postgresql.conf`: `listen_addresses` diubah `'*'` → `'localhost'` (backup dibuat dulu), service PG di-restart via elevated process (UAC). Teruji post-restart: psql & psycopg connect jalan sebagai `obliq_app`, `Get-NetTCPConnection` cuma listen `127.0.0.1`/`::1`
  - Riset manual DJPPR: ketemu endpoint API tersembunyi `api-djppr.kemenkeu.go.id/web/api/v1/media/{GUID}` yang balikin binary PDF hasil lelang; situs Angular SPA; `/robots.txt` balikin HTML SPA (bukan robots)
  - Riset manual BI: BI7DRR = tabel HTML paginated (`bi.go.id/id/statistik/indikator/bi-rate.aspx`, WebForms); JISDOR = tabel HTML paginated dengan filter periode
- Pending:
  - API key BPS nyata (blokir WAF belum resolve) → tetap skip fetcher BPS
  - Keputusan checkpoint sumber data: DJPPR (PDF parsing) & BI (HTML table) — validasi format persis menunggu Fase 1 fetch pertama
- Wajib direview Ghif:
  - Login manual `webapi.bps.go.id` via browser tanpa VPN → generate API key → isi `.env` `BPS_API_KEY`
  - Cek manual `/robots.txt` DJPPR via browser (aserssi kita: HTML SPA) + normalisasi User-Agent/email untuk scraper
  - Keputusan checkpoint: setuju lanjut Fase 1 dengan pola "DJPPR = PDF via api-media, BI = HTML table" setelah validasi 1 data point nyata
- Konsep finance baru: tidak ada yang baru sesi ini (riset struktur data, bukan logic finance).
- Catatan jujur: riset DJPPR/BI baru sampai level "struktur akses sumber" via riset web; kandungan isi PDF belum dicek parse-nya (belum ada fetch/unduh nyata ke session ini) — dikerjakan di awal Fase 1.

### 2026-08-10 — Sesi 3 (keamanan role DB + dashboard minimal)
- Dikerjakan:
  - Dibuat role `obliq_app` (LOGIN + password) + grant hanya ke `obliq_db`: CONNECT, USAGE+CREATE schema public, CRUD semua tabel/sequence + default privileges utk migrasi Fase 1. `.env` & `.env.example` diupdate ke `obliq_app`
  - Verifikasi teruji: psql & psycopg connect sebagai `obliq_app`, baca 6 baris, seed ulang jalan (write access) — semua sebagai role baru, bukan `postgres`
  - Cek `postgresql.conf`: `listen_addresses='*'` + `pg_hba.conf` (trust hanya 127.0.0.1/::1) — dilaporkan, BELUM diubah (nunggu konfirmasi Ghif)
  - `dashboard/app.py` minimal: baca `macro_indicators` → tabel + badge "DATA CONTOH — BELUM DARI SUMBER RESMI" utk source DUMMY/kosong (RULES.md §3). Ditambah streamlit+pandas ke requirements.txt
  - Teruji via Streamlit AppTest: 0 exception, 6 baris render, badge muncul. Juga smoke-test `streamlit run` headless (health 200)
- Pending:
  - API key BPS nyata (blokir WAF belum resolve)
  - `listen_addresses='*'` → keputusan akan diubah jadi `localhost` (nunggu konfirmasi Ghif)
  - Riset DJPPR & BI (sesi berikut)
- Wajib direview Ghif:
  - Konfirmasi setuju ubah `listen_addresses` → `localhost` (+ restart service PG) atau biarkan
  - Login manual `webapi.bps.go.id` via browser tanpa VPN → generate API key → isi `.env` `BPS_API_KEY`
  - Verifikasi visual dashboard: `streamlit run dashboard/app.py`
- Konsep finance baru: tidak ada yang baru sesi ini.
- Catatan jujur: dashboard baru di-test via AppTest (berjalan, render benar) tapi belum dilihat visual langsung di browser oleh Ghif.

### 2026-08-10 — Sesi 2 (setup + seed dummy + blocker BPS)
- Dikerjakan:
  - Rebuild setup yang tidak jadi di sesi 1: struktur folder penuh (`pipeline/`, `api/`, `dashboard/`, `db/migrations` sesuai ARCHITECTURE.md §3), `.venv` + `requirements.txt` (sqlalchemy, psycopg[binary], python-dotenv), `.env` + `.env.example` (`DATABASE_URL` local trust auth)
  - Verifikasi koneksi PostgreSQL: `obliq_db` (PG 17) terbaca, query berhasil
  - `db/connection.py` (bootstrap engine, belum ada model)
  - `db/seed_dummy_data.py` — 6 baris inflasi YoY dummy, `source='DUMMY_CONTOH'`, value pakai `Decimal`, idempoten (re-run replace baris DUMMY saja). Teruji: seed berhasil, query verifikasi 6 baris, re-run tetap 6 baris (bukan dobel)
  - Update RULES.md §3: aturan render data wajib `source` jelas; `DUMMY*`/kosong → badge "DATA CONTOH — BELUM DARI SUMBER RESMI"
  - Catat blocker BPS di "Diketahui Bermasalah"
- Pending:
  - API key BPS nyata (blokir WAF belum resolve)
  - Riset DJPPR & BI (sengaja dibiarkan ke sesi berikutnya — scope sesi ini terbatas)
- Wajib direview Ghif:
  - **Akses `webapi.bps.go.id` manual via browser tanpa VPN** → generate API key → isi `.env` `BPS_API_KEY`
  - Konfirmasi `DATABASE_URL` di `.env` cocok dengan setup PG lokal
- Konsep finance baru: tidak ada yang baru sesi ini (belum ada logic finance).
- Catatan jujur: setup pada "sesi 1" ternyata tidak pernah materialisasi di disk (hanya planning). Sesi ini yang benar-benar membuat folder/venv/koneksi.
