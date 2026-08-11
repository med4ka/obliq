# ARCHITECTURE.md — Obliq

## 1. Prinsip Kunci

Ini project **data-first**, bukan CRUD app biasa — arsitekturnya dipisah jelas jadi 2 dunia yang beda kebutuhan:

```
[Sumber Data Eksternal]
        ↓
[PIPELINE: Fetch → Validate → Transform → Store]  ← jalan terjadwal, tidak sinkron dengan user
        ↓
[Database — sumber kebenaran]
        ↓
[APLIKASI: API + Dashboard]  ← dibaca user, TIDAK PERNAH fetch langsung ke sumber eksternal
```

Kenapa dipisah tegas begini: dashboard yang di-load user tidak boleh menunggu scraping selesai (lambat, dan sumber eksternal bisa down). Pipeline jalan di jadwal sendiri (cron/scheduler), user selalu baca dari database lokal yang sudah tervalidasi.

## 2. Tech Stack

| Layer | Teknologi | Alasan |
|---|---|---|
| Pipeline/ETL | Python (`requests`/`httpx`, `BeautifulSoup`/`lxml` untuk scraping, `Pydantic` untuk validasi) | Python native untuk data work, ekosistem scraping paling matang |
| Scheduler | `APScheduler` (Fase 1-3) → cron/Airflow kalau sudah kompleks (Fase 4+) | Jangan over-engineer di awal — APScheduler cukup untuk jadwal harian/mingguan sederhana |
| Database | PostgreSQL | Time-series data (yield harian) + relational (issuer, bond metadata) cocok di Postgres, tidak perlu database khusus time-series di skala ini |
| ORM | `SQLAlchemy` + `Alembic` untuk migration | Standar Python, mirip fungsinya dengan GORM di project-project Go sebelumnya |
| API layer | `FastAPI` | Type-safe (Pydantic terintegrasi), async-ready untuk nanti kalau perlu, dokumentasi API otomatis |
| Dashboard (Fase 1-3) | `Streamlit` | Cepat dibangun untuk dashboard data-heavy, native Python (tidak perlu belajar stack frontend terpisah di tengah belajar finance) |
| Dashboard (Fase 4, kalau perlu lebih custom) | Evaluasi ulang saat itu — mungkin tetap Streamlit, mungkin pindah ke Next.js kalau butuh UX lebih custom (skill yang sudah dikuasai dari project sebelumnya) | Keputusan ditunda, jangan diputuskan sekarang |
| Precision numerik | `Decimal` (stdlib Python), BUKAN `float` | Wajib untuk semua nilai finansial (SYSTEM.md §1 poin 5) |

## 3. Struktur Folder (Target)

```
obliq/
├── pipeline/
│   ├── fetchers/          # satu file per sumber data (kemenkeu.py, bi.py, bps.py, dst)
│   ├── validators/         # skema Pydantic per sumber
│   ├── transformers/       # normalisasi ke skema internal
│   ├── storage/            # write ke database
│   └── scheduler.py        # orkestrasi jadwal fetch
│
├── api/
│   ├── routers/            # endpoint per domain (yield-curve, macro, bonds)
│   ├── services/            # business logic (kalkulasi spread, dst)
│   └── main.py
│
├── dashboard/
│   └── app.py              # Streamlit entry point + halaman-halaman
│
├── db/
│   ├── models.py            # SQLAlchemy models
│   └── migrations/          # Alembic
│
├── SYSTEM.md, RULES.md, PRD.md, ARCHITECTURE.md, SCHEMA.md, DESIGN.md, PROGRESS.md
```

## 4. Prinsip Data Pipeline (Detail)

Setiap fetcher WAJIB mengikuti kontrak yang sama:
```python
def fetch() -> RawData:
    """Ambil data mentah dari sumber. Timeout + retry wajib."""

def validate(raw: RawData) -> ValidatedData:
    """Pydantic schema check. Gagal validasi = raise, JANGAN masuk ke transform."""

def transform(data: ValidatedData) -> InternalSchema:
    """Normalisasi ke skema internal (lihat SCHEMA.md)."""

def store(data: InternalSchema) -> None:
    """Upsert ke DB, idempotent (fetch ulang tanggal yang sama = update, bukan duplikat)."""
```

**Idempotency itu wajib**, sama prinsipnya dengan idempotency key di project-project sebelumnya (booking system) — kalau job scheduler retry atau dijalankan manual ulang, tidak boleh menghasilkan data dobel.

**Gap handling:** kalau 1 hari sumber data gagal di-fetch (situs down, format berubah), JANGAN interpolasi nilai yang hilang secara diam-diam. Simpan sebagai gap eksplisit (lihat SCHEMA.md, field `is_estimated` atau tabel log terpisah), dan dashboard harus menampilkan gap itu apa adanya (garis putus di chart, bukan disambung mulus seolah data lengkap).

## 5. Keamanan & Privasi

- Ini bukan aplikasi dengan data pengguna sensitif di Fase 1-3 (belum ada auth) — risiko keamanan utama di fase awal adalah **integritas data**, bukan privasi user.
- Kalau Fase 4 (auth, watchlist personal) dikerjakan: reuse pola yang sudah teruji dari project sebelumnya — JWT httpOnly cookie, bcrypt, rate limiting di endpoint auth.
- API publik (kalau dibuka untuk pihak ketiga sebagai bagian monetisasi) WAJIB rate-limited dan API-key-based, bukan terbuka tanpa batas.

## 6. Deployment (Dipikirkan Nanti, Dicatat Sekarang)

Untuk MVP (Fase 1), jalankan lokal dulu (scheduler + Streamlit di laptop/server kecil). Kalau sudah stabil dan mau publik, opsi murah: Streamlit Community Cloud (gratis, untuk dashboard) + database terpisah (Supabase/Railway free tier) + scheduler di VPS kecil atau GitHub Actions cron (untuk pipeline). Keputusan detail ditunda sampai Fase 1 selesai — jangan optimasi deployment sebelum ada yang perlu di-deploy.
