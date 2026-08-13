import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { BondCompareChart } from "@/components/chart/lazy-charts";
import ChartModal from "@/components/chart-modal";

interface Props {
  searchParams: Promise<{ seri?: string }>;
}

export const metadata: Metadata = {
  title: "Bandingkan Obligasi",
  description: "Bandingkan yield historis beberapa seri obligasi pemerintah secara side-by-side.",
  alternates: { canonical: "/obligasi/bandingkan" },
};

export default async function BondComparePage({ searchParams }: Props) {
  const { seri } = await searchParams;
  const codes = seri ? seri.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean) : [];

  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Kembali ke kurva yield
      </Link>

      <p className="mt-6 font-mono text-xs uppercase tracking-widest text-ink-muted">
        Perbandingan Obligasi
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Bandingkan Yield Obligasi
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Bandingkan yield historis beberapa seri SUN secara side-by-side.
      </p>

      {codes.length < 2 ? (
        <div className="mt-8">
          <p className="font-mono text-xs text-ink-muted">
            Masukkan kode seri obligasi di URL, misal: <code className="text-ledger-green">/obligasi/bandingkan?seri=FR0100,FR0101</code>
          </p>
          <form
            className="mt-4 flex flex-wrap items-end gap-2"
            action="/obligasi/bandingkan"
          >
            <label className="flex flex-col gap-1 font-mono text-xs text-ink-muted">
              Kode seri (koma pisah)
              <input
                type="text"
                name="seri"
                placeholder="FR0100,FR0101"
                className="w-48 rounded-md border border-ink/20 bg-surface px-2.5 py-1.5 font-mono text-sm text-ink outline-none focus:border-ledger-green"
              />
            </label>
            <button
              type="submit"
              className="rounded-md border border-ledger-green bg-ledger-green px-3 py-1.5 font-mono text-xs text-parchment transition-colors hover:bg-ledger-green/90"
            >
              Bandingkan
            </button>
          </form>
        </div>
      ) : (
        <div className="mt-8">
          <p className="font-mono text-xs text-ink-muted">
            Membandingkan: {codes.join(", ")}
          </p>
          <div className="mt-3">
            <ChartModal label={`Perbandingan obligasi: ${codes.join(", ")}`}>
              <BondCompareChart codes={codes} />
            </ChartModal>
          </div>
        </div>
      )}
    </section>
  );
}
