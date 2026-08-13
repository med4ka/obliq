import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Belajar",
  description:
    "Glosarium istilah obligasi, saham, dan pasar modal Indonesia — dalam bahasa yang mudah dipahami.",
  alternates: {
    canonical: "/belajar",
  },
};

const TERMS = [
  {
    term: "Obligasi (Bond)",
    def: "Surat utang. Penerbit (pemerintah atau perusahaan) pinjam uang dari investor, janji bayar bunga berkala (kupon) dan mengembalikan pokok utang saat jatuh tempo. Beda dari saham — obligasi bukan kepemilikan, cuma pinjaman.",
  },
  {
    term: "Sukuk",
    def: "Versi syariah dari obligasi. Secara struktur legal beda (bagi hasil/sewa aset, bukan bunga eksplisit), tapi secara fungsi ekonomi (arus kas ke investor, jatuh tempo, risiko) mirip obligasi konvensional. Indonesia adalah penerbit Sukuk negara terbesar di dunia.",
  },
  {
    term: "Tenor",
    def: "Jangka waktu sampai jatuh tempo. Misal obligasi 10 tahun = tenor 10 tahun. Makin panjang tenor, makin tinggi yield-nya (kompensasi risiko waktu).",
  },
  {
    term: "Kupon (Coupon Rate)",
    def: "Persentase bunga TETAP yang dijanjikan penerbit, dihitung dari nilai nominal obligasi. Angka ini dicetak di kontrak dan tidak berubah selama umur obligasi.",
  },
  {
    term: "Yield",
    def: "Ini yang SERING disalahpahami. Yield BUKAN sama dengan kupon. Yield adalah imbal hasil EFEKTIF kalau kamu beli obligasi SEKARANG di harga pasar dan pegang sampai jatuh tempo. Kalau harga obligasi turun, yield-nya NAIK — karena kamu bayar lebih murah untuk arus kas kupon yang sama. Harga dan yield selalu bergerak berlawanan arah.",
  },
  {
    term: "Kurva Yield (Yield Curve)",
    def: "Grafik yield vs tenor untuk 1 penerbit (biasanya pemerintah). Normalnya naik (tenor lebih panjang = yield lebih tinggi). Kalau kurva TERBALIK (tenor pendek yield lebih tinggi dari tenor panjang) — itu sinyal yang secara historis sering mendahului resesi.",
  },
  {
    term: "Credit Spread",
    def: "Selisih (dalam basis poin) antara yield obligasi KORPORASI dikurangi yield obligasi PEMERINTAH di tenor yang SAMA. Makin berisiko perusahaan, makin lebar spread-nya. Spread yang melebar tajam adalah sinyal awal pasar mulai khawatir.",
  },
  {
    term: "Basis Poin (bps)",
    def: "1 bps = 0,01%. Dipakai karena perubahan yield/spread biasanya kecil — 'spread melebar 45 bps' lebih presisi daripada '0,45%'.",
  },
  {
    term: "Lelang (Auction)",
    def: "Mekanisme pemerintah menerbitkan SUN. Investor menawarkan harga/yield via sistem lelang, pemerintah memilih berdasarkan pesanan terbaik. Hasil per seri adalah yield rata-rata tertimbang yang dimenangkan (Weighted Average Yield).",
  },
  {
    term: "SPN (Surat Perbendaharaan Negara)",
    def: "Obligasi pemerintah jangka pendek (jatuh tempo < 1 tahun, biasa 3/6/12 bulan). Dijual dengan diskonto (tanpa kupon) — investor beli di bawah nominal, untung dari selisih saat jatuh tempo.",
  },
  {
    term: "FR (Fixed-Rate)",
    def: "Seri SUN berjangka panjang (2–30+ tahun) dengan kupon tetap. Inilah seri 'benchmark' yang membentuk kurva yield. Seri FR sering di-reopen (lelang ulang) untuk menambah likuiditas.",
  },
  {
    term: "Bid-to-Cover Ratio",
    def: "Rasio total penawaran yang masuk dibagi total yang dimenangkan. Misal 2,18 berarti penawaran 2,18× dari yang diterima. Angka > 2–3 sering dianggap indikator permintaan yang kuat.",
  },
  {
    term: "IHK (Indeks Harga Konsumen)",
    def: "Ukuran tingkat harga rata-rata barang/jasa yang dikonsumsi rumah tangga, dalam bentuk indeks (bukan persen). IHK adalah bahan baku inflasi: naiknya IHK dari satu periode ke periode lain menunjukkan inflasi.",
  },
  {
    term: "Inflasi YoY vs MtM",
    def: "YoY (year-on-year): IHK bulan ini dibanding IHK bulan yang sama tahun lalu — menunjukkan tren 12 bulan. MtM (month-on-month): IHK bulan ini dibanding bulan sebelumnya — menunjukkan tekanan harga terbaru, tapi lebih berisik karena faktor musiman.",
  },
  {
    term: "Saham (Stock/Equity)",
    def: "Bukti kepemilikan sebagian kecil dari perusahaan. Pemegang saham adalah 'pemilik' — berhak atas keuntungan lewat dividen dan kenaikan nilai, tapi juga menanggung risiko penuh. Beda fundamental dari obligasi.",
  },
  {
    term: "IHSG (Indeks Harga Saham Gabungan)",
    def: "Indeks pasar saham Indonesia yang menghitung rata-rata pergerakan harga SEMUA saham tercatat di BEI, dibobotkan kapitalisasi pasar. Ini 'termometer' utama pasar saham Indonesia.",
  },
  {
    term: "Kapitalisasi Pasar (Market Cap)",
    def: "Total nilai pasar perusahaan = jumlah saham beredar × harga saham. Dipakai sebagai bobot indeks — saham big-cap seperti BBCA lebih berat pengaruhnya ke IHSG daripada saham kecil.",
  },
  {
    term: "OHLC (Open-High-Low-Close)",
    def: "Data harga harian: harga pembukaan, tertinggi, terendah, dan penutupan. Volume = jumlah saham diperdagangkan hari itu. Untuk analisis jangka panjang, yang penting biasanya harga penutupan (close).",
  },
  {
    term: "Adjusted Close",
    def: "Harga penutupan yang sudah disesuaikan terhadap aksi korporasi (dividen, stock split). Wajib dipakai kalau mau menghitung return historis yang fair — kalau tidak, return kelihatan lebih kecil karena harga 'pangkas' saat ex-dividend.",
  },
  {
    term: "LQ45",
    def: "Indeks 45 saham paling likuid di BEI, diperbarui tiap 6 bulan (Februari & Agustus). Likuiditas = mudah diperjualbelikan tanpa mempengaruhi harga. LQ45 adalah tolok ukur (benchmark) kinerja saham blue-chip Indonesia.",
  },
];

export default function BelajarPage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
        Belajar
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Glosarium Pasar Modal
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Istilah-istilah pasar obligasi dan saham Indonesia, dirangkum dari PRD
        Obliq. Dibuat untuk siapa saja yang belajar bukan definisi
        textbook, tapi penjelasan yang langsung relevan dengan data di dashboard
        ini.
      </p>

      <div className="mt-8 rounded-lg border border-ink/10 bg-surface p-5 sm:p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
          Daftar istilah ({TERMS.length})
        </p>
        <dl className="mt-4 space-y-6">
          {TERMS.map(({ term, def }) => (
            <div key={term}>
              <dt className="font-serif text-base font-semibold text-ink">
                {term}
              </dt>
              <dd className="mt-1 text-sm leading-relaxed text-ink-muted">
                {def}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
