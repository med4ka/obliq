import type { Metadata } from "next";

import ChartModal from "@/components/chart-modal";
import { MacroBarChart, MacroChart } from "@/components/chart/lazy-charts";

export const metadata: Metadata = {
  title: "Indikator Makro",
  description:
    "Inflasi, suku bunga acuan, kurs, PDB, TPT, neraca perdagangan, dan cadangan devisa Indonesia.",
  alternates: {
    canonical: "/makro",
  },
};

const INDICATORS = [
  {
    type: "inflation_yoy",
    title: "Inflasi (YoY)",
    variant: "inflation" as const,
    note: "Data resmi BPS terpisah dari data contoh (DUMMY) yang digaris-putus.",
    context:
      "Grafik ini menunjukkan seberapa cepat harga barang naik dari tahun ke tahun.",
  },
  {
    type: "bi_7drr",
    title: "BI 7-Day Reverse Repo Rate",
    variant: "step" as const,
    note: "Nilai berlaku sampai keputusan berikutnya — digambar sebagai step.",
    context:
      "Grafik ini menunjukkan suku bunga acuan Bank Indonesia — patokan umum biaya pinjam di Indonesia.",
  },
  {
    type: "usd_idr",
    title: "Kurs Referensi USD/IDR",
    variant: "daily" as const,
    note: "Fix harian JISDOR; tanggal tanpa fix ditampilkan sebagai gap.",
    context:
      "Grafik ini menunjukkan nilai tukar rupiah terhadap dolar AS.",
  },
  {
    type: "pdb_yoy",
    title: "PDB (Pertumbuhan YoY)",
    kind: "bar" as const,
    unit: "pct" as const,
    note: "Triwulanan, year-on-year, dari BPS.",
    context:
      "Grafik ini menunjukkan laju pertumbuhan ekonomi Indonesia dari triwulan ke triwulan.",
  },
  {
    type: "trade_balance",
    title: "Neraca Perdagangan",
    kind: "bar" as const,
    unit: "usd" as const,
    note: "Bulanan, dalam juta USD. Positif = surplus, negatif = defisit.",
    context:
      "Grafik ini menunjukkan selisih ekspor dikurangi impor setiap bulan.",
  },
  {
    type: "tpt",
    title: "Tingkat Pengangguran Terbuka",
    variant: "sparse" as const,
    note: "Tahunan, rata-rata dua semester.",
    context:
      "Grafik ini menunjukkan persentase angkatan kerja yang aktif mencari kerja.",
  },
  {
    type: "foreign_reserves",
    title: "Cadangan Devisa",
    kind: "bar" as const,
    unit: "usd" as const,
    note: "Tahunan, dalam juta USD.",
    context:
      "Grafik ini menunjukkan total cadangan devisa nasional.",
  },
];

export default function MakroPage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
        Indikator Makro
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Indikator Makro
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Ringkasan indikator yang membentuk latar belakang pasar obligasi, dari
        sumber resmi (BPS, BI). Data contoh ditandai eksplisit.
      </p>

      <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {INDICATORS.map((indicator) => (
          <div key={indicator.type}>
            <h2 className="font-serif text-base font-semibold text-ink sm:text-lg">
              {indicator.title}
            </h2>
            <p className="mt-1 font-mono text-xs text-ink-muted">{indicator.note}</p>
            <p className="mt-2 text-sm text-ink-muted sm:text-base">
              {indicator.context}
            </p>
            <div className="mt-3">
              {"kind" in indicator && indicator.kind === "bar" ? (
                <ChartModal label={indicator.title}>
                  <MacroBarChart
                    indicatorType={indicator.type}
                    title={indicator.title}
                    unit={indicator.unit}
                    ariaLabel={`${indicator.title} — grafik`}
                  />
                </ChartModal>
              ) : (
                <ChartModal label={indicator.title}>
                  <MacroChart
                    indicatorType={indicator.type}
                    title={indicator.title}
                    variant={"variant" in indicator ? (indicator.variant as "inflation" | "step" | "daily" | "sparse") : "daily"}
                    ariaLabel={`${indicator.title} — grafik`}
                  />
                </ChartModal>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
