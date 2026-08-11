# RULES.md — Obliq

> Hidup di root repo, dibaca otomatis oleh coding agent. Konvensi teknis spesifik project ini — persona/gaya komunikasi ada di SYSTEM.md.

## 1. Sumber Data (Status per Fase 1 — akan bertambah)

| Sumber | Data | Cara akses | Catatan |
|---|---|---|---|
| DJPPR Kemenkeu | Hasil lelang SUN, outstanding debt | Situs publik (kemungkinan perlu scraping HTML/PDF, BUKAN API resmi) | Cek format sebelum bangun fetcher — situs pemerintah sering ubah struktur tanpa notice |
| Bank Indonesia (BI) | BI7DRR, kurs referensi, data JIBOR | Situs publik BI, ada beberapa dataset dalam format Excel/CSV yang bisa diunduh terjadwal | |
| BPS (Badan Pusat Statistik) | Inflasi (IHK/YoY) | `webapi.bps.go.id` — BPS punya API resmi dengan API key gratis (daftar dulu) | Sumber paling ramah dibanding yang lain, prioritaskan pola ini |
| IBPA | Yield obligasi korporasi granular | **BELUM ADA akses gratis dikonfirmasi** — riset Fase 2 | Jangan asumsikan bisa diakses sebelum dicek langsung |

**Aturan scraping (berlaku untuk semua fetcher):**
- Cek `robots.txt` situs sumber sebelum scraping, hormati aturan di sana
- User-Agent jujur, sertakan cara kontak (misal email) di header kalau situs itu menyediakan tempatnya
- Rate limit sendiri — jangan hajar server pemerintah/publik dengan request bertubi-tubi meskipun secara teknis bisa
- Cache/simpan HTML mentah yang di-scrape (opsional tapi disarankan) — kalau parsing gagal, bisa debug tanpa fetch ulang

## 2. Konvensi Kode Python

- Semua nilai finansial: `Decimal`, bukan `float` — lihat SYSTEM.md §1 poin 5. Ini termasuk di level Pydantic schema (`condecimal` atau `Decimal` dengan validator) dan SQLAlchemy model (`Numeric`, bukan `Float`).
- Type hints wajib di semua fungsi baru — ini project belajar juga, type hints membantu Ghif belajar bentuk data yang benar.
- Docstring di setiap fetcher/transformer menjelaskan APA yang di-fetch dan DARI MANA (sumber resmi), bukan cuma "fetches data".
- `pytest` untuk testing — minimal test untuk: parsing/transform logic (data sample → hasil yang diharapkan), dan validasi Pydantic schema menolak data yang salah bentuk.

## 3. Keputusan Teknis yang Sudah Diambil (jangan diusulkan ulang)

- **Decimal, bukan float**, untuk semua nilai finansial — non-negotiable, alasan di SYSTEM.md §1 poin 5.
- **Pipeline dan aplikasi dipisah tegas** — dashboard tidak pernah fetch langsung ke sumber eksternal, selalu baca dari database (ARCHITECTURE.md §1).
- **Gap data tidak diinterpolasi diam-diam** — default adalah menampilkan gap apa adanya, `is_estimated` flag dipakai sangat jarang dengan alasan eksplisit.
- **Streamlit untuk dashboard MVP** (Fase 1-3), bukan Next.js — biar fokus belajar data/finance dulu tanpa kompleksitas frontend terpisah. Next.js dipertimbangkan lagi di Fase 4 kalau memang perlu.
- **Tidak ada rekomendasi beli/jual** di fitur manapun — batasan produk sekaligus legal (SYSTEM.md §1 poin 4).
- **Render data wajib punya jejak sumber yang jelas** — tiap angka yang ditampilkan harus membawa `source` + tanggal data. Data yang `source`-nya kosong/tdk jelas, ATAU diawali `DUMMY`, WAJIB dirender dengan badge/label mencolok **"DATA CONTOH — BELUM DARI SUMBER RESMI"** dan TIDAK boleh dicampur rata dengan data asli dalam satu statistik/agregat yang sama.

## 4. Yang Perlu Direview Manual oleh Ghif (prioritas tinggi)

- Logic transform/normalisasi data dari tiap sumber — data pemerintah sering punya quirk format (misal tanggal dalam format lokal, angka pakai koma sebagai desimal bukan titik) yang gampang salah parse tanpa ketahuan
- Kalkulasi spread (Fase 3) — pastikan benchmark tenor yang dipilih benar-benar tenor terdekat, bukan asal ambil
- Bahasa di fitur anomaly flag — pastikan selalu netral/deskriptif, tidak pernah kebablasan jadi rekomendasi aksi

## 5. Belajar Finance Sambil Jalan

Setiap kali menemukan istilah/konsep finance baru yang belum ada di PRD.md §1 (primer), AI WAJIB menambahkannya ke situ dengan penjelasan singkat — primer itu dokumen hidup, bukan ditulis sekali lalu dilupakan.
