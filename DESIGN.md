# DESIGN.md — Obliq Design System

## 0. IDENTITAS: "SERTIFIKAT, BUKAN TERMINAL TRADING"

Kesalahan paling umum di tool finance bikinan sendiri (atau bikinan AI): niru Bloomberg Terminal murahan — dark mode pekat, angka hijau/merah neon berkedip, font Inter, card dengan glow border. Ini pola yang sama persis di semua "trading dashboard" AI-generated — instant terasa generik.

Obliq berangkat dari sudut pandang berbeda: **obligasi, secara historis, adalah benda fisik** — sertifikat kertas dengan border ornamen rumit (*guilloché* — pola garis berulang presisi tinggi yang dipakai di uang kertas dan sertifikat resmi, awalnya untuk mencegah pemalsuan), tanda tangan, meterai, nomor seri. ini dokumen yang dipercaya secara visual sebelum era digital. Obliq mengambil bahasa visual itu — bukan buat nostalgia, tapi karena itu secara alami mengomunikasikan **kepercayaan dan formalitas**, dua hal yang justru dibutuhkan tool finance, tanpa harus niru estetika terminal trading yang sudah terlalu umum.

**DILARANG KERAS:**
- Dark mode sebagai default dengan aksen neon hijau/merah untuk naik/turun (klise #1 dashboard finance AI-generated)
- Font Inter sebagai typeface utama
- Card dengan glow/shadow neon, glassmorphism berlebihan
- Angka besar dengan animasi "count up" di setiap load — norak dan mengganggu kalau dipakai di semua tempat sekaligus

## 1. Palet Warna

### Base (Light Mode — "Kertas Sertifikat", default & utama)
| Token | Hex | Fungsi |
|---|---|---|
| `parchment` | `#F6F1E7` | Background utama — kertas krem hangat, evokasi kertas sertifikat lama |
| `ink` | `#1F2419` | Teks utama — hitam-hijau tua, seperti tinta cetak sertifikat |
| `ink-muted` | `#6B6355` | Teks sekunder |
| `ledger-green` | `#0F4C3A` | Aksen utama — warna hijau tua klasik yang dipakai di sertifikat/uang kertas asli (bukan hijau neon "profit" yang klise) |
| `surface` | `#FFFEF9` | Card/panel |

### Status (dipakai sangat sedikit, dan spesifik)
| Token | Hex | Fungsi |
|---|---|---|
| `seal-red` | `#8C2F1F` | HANYA untuk anomaly flag (spread melebar signifikan) — seperti cap/stempel resmi, bukan warna "merah = rugi" yang berkedip di semua tempat |
| `gold-verified` | `#A67C27` | HANYA untuk indikator "data terverifikasi/sumber resmi" — aksen langka, seperti foil emas di sertifikat asli |

**Catatan eksplisit soal naik/turun:** JANGAN pakai hijau/merah standar untuk representasi "yield naik = baik/buruk" — yield naik itu AMBIGU (bisa baik untuk investor baru, buruk untuk pemegang lama karena harga turun). Representasikan perubahan dengan **arah panah + angka**, netral secara warna (pakai `ink`/`ink-muted`), bukan pewarnaan otomatis hijau-merah yang menyiratkan penilaian "bagus/jelek" yang sebenarnya tidak akurat secara finansial.

## 2. Tipografi

| Peran | Font | Alasan |
|---|---|---|
| Heading/Display | **Source Serif 4** atau **Libre Caslon** | Serif dengan karakter dokumen resmi (dekat ke tipografi tercetak di sertifikat asli), BUKAN Playfair Display (klise AI) |
| Body/UI | **IBM Plex Sans** atau **Public Sans** | Humanist, netral, BUKAN Inter |
| Semua angka (yield, spread, harga, tanggal) | **IBM Plex Mono** | Tabular figures — presisi visual untuk data yang sering dibandingkan berdampingan |

## 3. Motif Guilloché (Signature Element, Dipakai Terbatas)

Pola garis geometris presisi tinggi (mirip pola di uang kertas Rupiah atau sertifikat saham lama) sebagai border tipis di sekitar card "obligasi individual" (bukan semua card) — dan sebagai watermark sangat samar (opacity rendah) di header dashboard utama. **Hanya 2 tempat ini** — kalau dipakai di semua elemen, dia jadi dekorasi generik dan kehilangan makna sebagai signature (prinsip yang sama seperti garis rute di project sebelumnya).

## 4. Layout & Chart Styling

- **Kurva yield sebagai hero visual** — bukan tabel angka duluan, chart duluan. Line chart dengan sumbu X = tenor, sumbu Y = yield, styling minimal (garis `ledger-green` tegas, grid halus, TANPA gradient fill di bawah garis yang norak).
- **Setiap chart WAJIB ada caption sumber + tanggal data** di bawahnya, kecil tapi selalu ada — bukan disembunyikan di tooltip.
- **Gap data**: render sebagai garis putus-putus di chart pada rentang tanggal yang datanya hilang, JANGAN disambung mulus (ARCHITECTURE.md §4).
- **Skeleton loading**: bentuk chart placeholder (garis abu-abu bergelombang), bukan blok generik.

## 5. Nada Konten (Tone)

Bahasa di seluruh UI **netral dan deskriptif**, tidak pernah preskriptif. "Spread melebar 45 bps dalam 30 hari" — BUKAN "Waspada, obligasi ini berisiko". Ini bukan cuma gaya menulis, ini kepatuhan terhadap SYSTEM.md §1 poin 4 (bukan penasihat investasi).

## 6. Aksesibilitas
- Kontras warna dicek terutama untuk `ink-muted` di atas `parchment` (rasio minimal 4.5:1)
- Chart tidak boleh HANYA mengandalkan warna untuk membedakan seri data (obligasi berbeda) — pakai juga pola garis (solid/dashed) atau label langsung
