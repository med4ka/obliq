# SCHEMA.md — Obliq

## Skema Database (PostgreSQL + SQLAlchemy)

Prinsip kunci: setiap observasi angka (yield, indikator makro) WAJIB punya `source` dan `fetched_at` — jejak audit itu bagian dari produk, bukan cuma metadata teknis (lihat SYSTEM.md §1 poin 2-3).

### `bonds`
Metadata obligasi/Sukuk — tidak berubah setiap hari, cuma sekali diisi per instrumen.

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| code | varchar, unique | Kode/ISIN obligasi |
| name | varchar | Nama instrumen |
| type | enum | `government` / `corporate` / `sukuk_government` / `sukuk_corporate` |
| issuer_id | FK ke `issuers`, nullable | Null untuk obligasi pemerintah |
| coupon_rate | Decimal(6,4), nullable | Kupon tetap (%), null kalau zero-coupon |
| issue_date | date | |
| maturity_date | date | |
| tenor_years | Decimal(5,2) | Dihitung dari issue/maturity, disimpan untuk query cepat |
| is_active | bool | Soft flag, obligasi yang sudah jatuh tempo tetap disimpan untuk histori |

### `issuers`
Untuk obligasi korporasi.

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| name | varchar | Nama perusahaan |
| sector | varchar | Sektor industri (untuk agregasi spread per sektor nanti) |
| ticker | varchar, nullable | Kalau perusahaan publik, ticker sahamnya (untuk cross-reference) |

### `yield_observations`
Tabel inti — 1 baris per obligasi per tanggal observasi. Ini tabel yang paling sering ditulis (harian) dan paling sering dibaca (chart historis).

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| bond_id | FK ke `bonds` | |
| observation_date | date | Tanggal data ini berlaku (BUKAN tanggal fetch) |
| yield_value | Decimal(8,4) | Dalam persen, presisi tinggi karena dipakai hitung spread |
| price | Decimal(12,4), nullable | Harga per 100 nilai nominal, kalau tersedia dari sumber |
| source | varchar | Nama sumber data (misal "DJPPR", "BI") |
| fetched_at | timestamp | Kapan pipeline benar-benar mengambil data ini |
| is_estimated | bool, default false | WAJIB true kalau nilai ini hasil interpolasi (lihat ARCHITECTURE.md §4 — pakai ini SANGAT jarang dan selalu dengan alasan jelas, prinsip default adalah TIDAK mengisi gap) |
| Unique constraint | (bond_id, observation_date) | Idempotency — fetch ulang tanggal sama = update, bukan insert baru |

### `macro_indicators`
Indikator makro yang tidak terikat ke 1 obligasi spesifik.

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| indicator_type | enum | `inflation_yoy` / `bi_7drr` / `usd_idr` / dst (perluas sesuai kebutuhan) |
| observation_date | date | |
| value | Decimal(12,4) | |
| source | varchar | |
| fetched_at | timestamp | |
| Unique constraint | (indicator_type, observation_date) | |

### `credit_spreads` (Fase 3)
Spread yang sudah dihitung, disimpan (bukan cuma dihitung on-the-fly) supaya chart historis cepat dan konsisten meskipun kurva benchmark berubah nanti.

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| corporate_bond_id | FK ke `bonds` | |
| benchmark_bond_id | FK ke `bonds` | Obligasi pemerintah dengan tenor terdekat yang dipakai sebagai pembanding |
| observation_date | date | |
| spread_bps | Decimal(8,2) | Dalam basis poin (lihat PRD.md primer) |
| calculated_at | timestamp | |
| Unique constraint | (corporate_bond_id, observation_date) | |

### `anomaly_flags` (Fase 3)
Deteksi spread yang melebar signifikan — disimpan sebagai OBSERVASI, framing bahasa harus netral (lihat SYSTEM.md §1 poin 4, ini bukan sinyal beli/jual).

| Kolom | Tipe | Catatan |
|---|---|---|
| id | UUID/serial | PK |
| bond_id | FK ke `bonds` | |
| flagged_date | date | |
| change_bps | Decimal(8,2) | Perubahan spread dalam periode yang diamati |
| period_days | int | Periode pengamatan (misal 30 hari) |
| description | text | Bahasa netral: "Spread melebar 45 bps dalam 30 hari terakhir" — BUKAN "Jual sekarang" |

### `users` + `watchlists` (Fase 4, kalau dikerjakan)
Reuse pola dari project sebelumnya — `users` (email, password_hash, created_at), `watchlists` (user_id FK, bond_id FK, unique constraint keduanya).

## Prinsip Umum
- Semua tabel observasi (`yield_observations`, `macro_indicators`, `credit_spreads`) itu **append/upsert, tidak pernah destructive update** tanpa jejak — kalau data direvisi sumbernya, pertimbangkan tabel versi/histori daripada overwrite diam-diam, supaya tetap bisa ditelusuri "dulu datanya bilang apa".
- `Decimal`, bukan `float`, untuk SEMUA kolom numerik finansial (SYSTEM.md §1 poin 5) — ini berlaku di level SQLAlchemy model juga (pakai `sqlalchemy.Numeric`, bukan `Float`).
