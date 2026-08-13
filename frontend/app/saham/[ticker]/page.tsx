import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { StockChart } from "@/components/chart/lazy-charts";
import ChartModal from "@/components/chart-modal";

interface Props {
  params: Promise<{ ticker: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ticker } = await params;
  return {
    title: `${ticker.toUpperCase()}`,
    description: `Harga historis saham ${ticker.toUpperCase()} — data dari Yahoo Finance.`,
    alternates: { canonical: `/saham/${ticker}` },
  };
}

export default async function StockDetailPage({ params }: Props) {
  const { ticker } = await params;
  const code = ticker.toUpperCase();

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
        {code}
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        {code}
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Pergerakan harga saham {code} dari waktu ke waktu. Data harian dari
        Yahoo Finance.
      </p>

      <div className="mt-8">
        <ChartModal label={`${code} — Historis`}>
          <StockChart ticker={code} />
        </ChartModal>
      </div>
    </section>
  );
}
