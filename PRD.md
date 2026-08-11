# PRD.md — Obliq

## 0. Ringkasan Satu Paragraf

Obliq adalah dashboard analitik pasar obligasi Indonesia — dimulai dari kurva yield obligasi pemerintah (SUN) dan indikator makroekonomi, dengan target berkembang ke analisis credit spread obligasi korporasi & Sukuk begitu sumber data yang layak ditemukan. Dibangun sebagai project belajar (Ghif belajar finance + data engineering sekaligus) sekaligus tool yang genuinely berguna untuk mahasiswa finance, analis junior, dan investor ritel yang mulai serius ke fixed income — segmen yang saat ini cuma punya akses ke Bloomberg Terminal (mahal, institusional) atau tidak sama sekali.

## 1. Primer Finance (Baca Ini Dulu — Untuk Ghif, Bukan Cuma Dokumentasi)

Ini bukan basa-basi — ini fondasi konsep yang dipakai di seluruh dokumen lain. Kalau ada istilah yang masih belum jelas pas baca dokumen lain, balik ke sini.

**Obligasi (bond):** surat utang. Penerbit (pemerintah atau perusahaan) pinjam uang dari investor, janji bayar bunga berkala (disebut *kupon*) dan mengembalikan pokok utang saat jatuh tempo (*maturity*). Beda dari saham — obligasi bukan kepemilikan, cuma pinjaman.

**Sukuk:** versi syariah dari obligasi. Secara struktur legal beda (bagi hasil/sewa aset, bukan bunga eksplisit — karena riba dilarang), tapi secara fungsi ekonomi (arus kas ke investor, jatuh tempo, risiko) mirip obligasi konvensional. Indonesia adalah penerbit Sukuk negara terbesar di dunia.

**Tenor:** jangka waktu sampai jatuh tempo (misal obligasi 10 tahun = tenor 10 tahun).

**Kupon (coupon rate):** persentase bunga TETAP yang dijanjikan penerbit, dihitung dari nilai nominal obligasi. Ini angka yang dicetak di kontrak, tidak berubah.

**Yield:** ini yang SERING disalahpahami. Yield BUKAN sama dengan kupon. Yield adalah imbal hasil EFEKTIF kalau kamu beli obligasi itu SEKARANG di harga pasar dan pegang sampai jatuh tempo — memperhitungkan harga beli (yang bisa di atas/di bawah nilai nominal). Kalau harga obligasi turun (karena permintaan pasar melemah), yield-nya NAIK — karena kamu bayar lebih murah untuk arus kas kupon yang sama. Harga dan yield selalu bergerak berlawanan arah.

**Kurva yield (yield curve):** grafik yield vs tenor untuk 1 penerbit (biasanya pemerintah, karena punya obligasi di banyak tenor). Normalnya naik (tenor lebih panjang = yield lebih tinggi, karena investor minta kompensasi lebih untuk risiko waktu yang lebih lama). Kalau kurva ini TERBALIK (tenor pendek yield-nya lebih tinggi dari tenor panjang) — itu sinyal yang secara historis sering mendahului resesi, karena artinya pasar mengharapkan kondisi ekonomi memburuk (dan suku bunga akan dipotong) di masa depan.

**Credit spread:** selisih (dalam basis poin) antara yield obligasi KORPORASI dikurangi yield obligasi PEMERINTAH di tenor yang SAMA. Obligasi pemerintah dianggap "bebas risiko gagal bayar" (risk-free), jadi spread ini representasi murni dari premi risiko kredit perusahaan itu — makin berisiko perusahaannya (secara persepsi pasar), makin lebar spread-nya. Spread yang tiba-tiba melebar tajam adalah sinyal awal pasar mulai khawatir soal kemampuan bayar perusahaan itu — biasanya jauh sebelum berita buruk resmi keluar.

**Basis poin (bps):** 1 bps = 0.01%. Dipakai karena perubahan yield/spread biasanya kecil (misal "spread melebar 45 bps" lebih presisi daripada "0.45%").

**Lelang (auction):** mekanisme pemerintah menerbitkan SUN — investor (Dealer Utama) menawarkan harga/yield via sistem lelang Bank Indonesia, pemerintah memilih (award) berdasarkan pesanan terbaik. Hasilnya per seri adalah *yield rata-rata tertimbang yang dimenangkan* (Weighted Average Yield) — inilah angka yang dipakai kurva yield, BUKAN kupon.

**SPN (Surat Perbendaharaan Negara):** obligasi pemerintah jangka pendek (jatuh tempo < 1 tahun, biasa 3/6/12 bulan). Dijual dengan **diskonto** (tanpa kupon — investor beli di bawah nominal, dapat untung dari selisih saat jatuh tempo), jadi `coupon_rate`-nya kosong/kosong di DB.

**FR (Fixed-Rate):** seri SUN berjangka panjang (2–30+ tahun) dengan **kupon tetap** — inilah seri "benchmark" yang membentuk kurva yield. Seri FR sering di-*reopen* (lelang ulang) untuk menambah likuiditas, jadi satu kode FR bisa muncul di banyak tanggal lelang.

**Bid-to-cover ratio:** rasio total penawaran yang masuk dibagi total yang dimenangkan (misal 2,18 berarti penawaran 2,18× dari yang diterima). Angka di atas 1 menunjukkan lelang "terisi" (permintaan melebihi yang ditawarkan); >2–3 sering dianggap indikator permintaan yang kuat. Konteks globalnya sama seperti *subscription ratio* di penawaran umum.

**IHK (Indeks Harga Konsumen):** ukuran tingkat harga rata-rata barang/jasa yang dikonsumsi rumah tangga, dalam bentuk indeks (angka indeks, bukan persen) dengan tahun dasar tertentu = 100. Di Indonesia, BPS menerbitkan IHK nasional dengan dasar 2018=100 untuk 90 kota. IHK adalah bahan baku inflasi: naiknya IHK dari satu periode ke periode lain menunjukkan harga-harga rata-rata naik, yaitu inflasi.

**Inflasi YoY (year-on-year) vs MtM (month-on-month):** dua cara umum membaca laju kenaikan harga:
- **YoY**: IHK bulan ini dibanding IHK bulan yang SAMA tahun lalu — `yoy = ((IHK_t - IHK_t12bulan_lalu) / IHK_t12bulan_lalu) × 100`. Menunjukkan tren inflasi 12 bulan, tidak terpengaruh musiman.
- **MtM**: IHK bulan ini dibanding IHK bulan SEBELUMNYA — `mtm = ((IHK_t - IHK_{t-1}) / IHK_{t-1}) × 100`. Menunjukkan tekanan harga paling baru, tapi lebih berisik karena faktor musiman (misal Lebaran, tahun ajaran).

**Kenapa Obliq menghitung sendiri YoY dari data IHK mentah alih-alih pakai angka "inflasi" jadi dari sumber:** BPS menyediakan inflasi MtM (var "Inflasi Bulanan M-to-M") dan indeks IHK, tapi TIDAK menyediakan var YoY siap pakai di API publiknya. Definisi YoY itu tetap dan sederhana, jadi Obliq menghitungnya dari indeks (SYSTEM.md §1 poin 2): setiap angka di dashboard bisa ditelusuri balik ke data sumber mentah, bukan hasil olahan yang tak bisa diverifikasi ulang. Kalau nanti BPS menyediakan var YoY resmi, kita tetap bisa mempertahankan hitungan sendiri dan membandingkannya (inti proyek belajar: mengerti ANGKA-nya, bukan cuma menampilkannya).

## 2. Masalah yang Diselesaikan

Data & analitik pasar obligasi Indonesia terkunci di 2 tempat: (a) layanan data berbayar institusional (IBPA, Bloomberg — harganya jutaan/bulan, di luar jangkauan individu), atau (b) tersebar di berbagai situs pemerintah dalam format yang tidak mudah dianalisis (PDF, tabel HTML tanpa API). Nyaris tidak ada tool publik yang menyatukan ini jadi dashboard yang bisa langsung dibaca — beda jauh dari pasar saham Indonesia yang sudah dilayani banyak app (Stockbit, Ajaib, dst).

## 3. Target Pengguna

- Mahasiswa/pelajar finance yang belajar fixed income tapi tidak akses Bloomberg Terminal kampus
- Analis junior di sekuritas/bank kecil yang butuh referensi cepat tanpa buka terminal mahal
- Investor ritel yang mulai serius masuk ke obligasi ritel (ORI, SBR, Sukuk Ritel) dan ingin konteks pasar
- Ghif sendiri, sebagai media belajar

## 4. Non-Goals (Sengaja TIDAK Dikerjakan)

- **Bukan platform trading** — tidak ada eksekusi transaksi beli/jual
- **Bukan penasihat investasi** — tidak ada rekomendasi "beli ini/jual itu" (lihat SYSTEM.md §1 poin 4, ini juga alasan legal)
- **Bukan real-time tick data** — data di-refresh berkala (harian/mingguan tergantung sumber), bukan streaming live seperti trading terminal
- **Bukan cakupan obligasi global** — fokus penuh ke pasar Indonesia

## 5. Scope Bertahap (JANGAN loncat fase)

### Fase 1 — Kurva Yield Pemerintah + Makro (fondasi, harus solid dulu)
- Scraping/fetch data lelang SUN & yield reference dari sumber publik (Kemenkeu/DJPPR, BI)
- Indikator makro: inflasi (BPS), suku bunga acuan BI7DRR, kurs USD/IDR
- Dashboard: kurva yield saat ini + historis (bisa lihat perubahan bentuk kurva dari waktu ke waktu)
- Glossary/edukasi terintegrasi (tooltip/halaman "Belajar" yang jelasin istilah dari primer di atas)

### Fase 2 — Riset & Validasi Sumber Data Korporasi (spike, bukan fitur)
- Riset eksplisit: sumber data yield/harga obligasi korporasi & Sukuk apa yang bisa diakses (prospektus IDX, keterbukaan informasi OJK, dst)
- Output fase ini adalah KEPUTUSAN (lanjut ke Fase 3 dengan sumber X, atau scope credit spread dikurangi/diubah), bukan kode

### Fase 3 — Credit Spread Analytics (tergantung hasil Fase 2)
- Hitung & tampilkan spread obligasi korporasi terpilih vs kurva pemerintah tenor sama
- Historical spread chart per emiten/sektor
- Flag anomali (spread melebar signifikan dalam periode singkat) — sebagai OBSERVASI DATA, bukan sinyal aksi (lihat SYSTEM.md §1 poin 4)

### Fase 4 — Publik & Monetisasi (opsional, side income)
- Auth (kalau mau watchlist personal)
- Tier gratis (kurva & makro dasar) vs berbayar (historical deep-dive, export data, alert email)

## 6. Metrik Keberhasilan (Longgar, Bukan KPI Formal)
- Fase 1: kurva yield ter-update otomatis tanpa intervensi manual selama 2 minggu berturut-turut
- Fase 3: minimal 5-10 obligasi korporasi dengan spread ter-track konsisten
- Fase 4: ada minimal 1 orang di luar Ghif yang pakai dan bilang ini berguna
