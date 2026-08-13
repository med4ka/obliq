import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { StockCompareChart } from "@/components/chart/lazy-charts";
import ChartModal from "@/components/chart-modal";

interface Props {
  searchParams: Promise<{ kode?: string }>;
}

export const metadata: Metadata = {
  title: "Bandingkan Saham",
  description: "Bandingkan pergerakan harga beberapa saham LQ45 secara side-by-side.",
  alternates: { canonical: "/saham/bandingkan" },
};

export default async function StockComparePage({ searchParams }: Props) {
  const { kode } = await searchParams;
  const tickers = kode ? kode.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) : [];

  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <Link
        href="/saham"
        className="inline-flex items-center gap-1 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Kembali ke daftar saham
      </Link>

      <p className="mt-6 font-mono text-xs uppercase tracking-widest text-ink-muted">
        Perbandingan Saham
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Bandingkan Saham
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Pilih saham dari tabel LQ45 dan bandingkan pergerakan harganya.
      </p>

      {tickers.length < 2 ? (
        <div className="mt-8 grid place-items-center rounded-md border border-dashed border-ink/10 bg-parchment px-4 py-12 font-mono text-xs text-ink-muted">
          Pilih minimal 2 saham dari tabel LQ45 dengan mencentang checkbox, lalu klik &quot;Bandingkan&quot;.
        </div>
      ) : (
        <div className="mt-8">
          <p className="font-mono text-xs text-ink-muted">
            Membandingkan: {tickers.join(", ")}
          </p>
          <div className="mt-3">
            <ChartModal label={`Perbandingan: ${tickers.join(", ")}`}>
              <StockCompareChart tickers={tickers} />
            </ChartModal>
          </div>
        </div>
      )}
    </section>
  );
}
