import type { Metadata } from "next";
import dynamic from "next/dynamic";
import Link from "next/link";
import { BarChart3 } from "lucide-react";

import ExplainerBox from "@/components/explainer-box";
import ChartModal from "@/components/chart-modal";
import { IhsgChart } from "@/components/chart/lazy-charts";

const Lq45Table = dynamic(() => import("@/components/chart/lq45-table"), {
  loading: () => (
    <div className="mt-6 space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-ink/5" />
      ))}
    </div>
  ),
});

export const metadata: Metadata = {
  title: "IHSG & LQ45",
  description:
    "Pergerakan IHSG dan daftar 45 saham paling likuid (LQ45) di Bursa Efek Indonesia.",
  alternates: {
    canonical: "/saham",
  },
};

export default function SahamPage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
        IHSG &amp; LQ45
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Indeks Harga Saham Gabungan
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Pergerakan IHSG dari waktu ke waktu — indeks utama yang mencerminkan
        seluruh saham tercatat di Bursa Efek Indonesia. Data harian dari Yahoo
        Finance.
      </p>

      <ExplainerBox title="Apa itu IHSG?" titleId="apa-itu-ihsg-heading">
        <p className="max-w-3xl text-sm leading-relaxed text-ink-muted sm:text-base">
          IHSG (Indeks Harga Saham Gabungan) adalah rata-rata pergerakan harga
          semua saham yang tercatat di Bursa Efek Indonesia. Kalau IHSG naik,
          artinya secara umum harga saham sedang menguat — dan sebaliknya. IHSG
          adalah &quot;termometer&quot; utama pasar saham Indonesia, dihitung
          setiap hari bursa dan menjadi acuan kinerja pasar modal secara
          keseluruhan.
        </p>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-muted sm:text-base">
          Data yang ditampilkan adalah harga penutupan (close) harian IHSG sejak
          tahun 2000, dari Yahoo Finance. Setiap titik adalah nilai IHSG di
          akhir hari perdagangan. Garis putus menandai hari libur bursa atau
          periode tanpa data — data tidak pernah diinterpolasi.
        </p>
      </ExplainerBox>

      <p className="mt-8 text-sm text-ink-muted sm:text-base">
        Grafik di bawah menunjukkan pergerakan IHSG sepanjang data yang
        tersedia —
      </p>
      <div className="mt-3">
        <ChartModal label="IHSG Historis">
          <IhsgChart ariaLabel="IHSG historis — grafik harga penutupan harian" />
        </ChartModal>
      </div>

      <section className="mt-12" aria-labelledby="lq45-heading">
        <h2
          id="lq45-heading"
          className="font-serif text-xl font-semibold text-ink sm:text-2xl"
        >
          45 Saham Paling Likuid (LQ45)
        </h2>
        <p className="mt-1 text-sm text-ink-muted sm:text-base">
          Daftar konstituen LQ45 — saham dengan kapitalisasi pasar dan nilai
          transaksi tertinggi di BEI, diperbarui setiap 6 bulan. Klik kode saham
          untuk melihat chart historis.
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          Sumber daftar: Wikipedia Indonesia (Mei-Juli 2026). Harga: Yahoo Finance.
        </p>
        <Link
          href="/saham/bandingkan"
          className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-ledger-green/30 bg-ledger-green/5 px-3.5 py-1.5 text-sm font-medium text-ledger-green transition-colors hover:border-ledger-green/60 hover:bg-ledger-green/10"
        >
          <BarChart3 className="h-4 w-4" aria-hidden />
          Bandingkan beberapa saham
        </Link>
        <Lq45Table />
      </section>
    </section>
  );
}
