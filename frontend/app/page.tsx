import type { Metadata } from "next";
import { BookOpen, GitCompare } from "lucide-react";
import Link from "next/link";

import ChartModal from "@/components/chart-modal";
import ExplainerBox from "@/components/explainer-box";
import JsonLd from "@/components/json-ld";
import { YieldCurveChart, YieldHistoryChart } from "@/components/chart/lazy-charts";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "Obliq",
  description:
    "Kurva imbal hasil (yield) obligasi pemerintah Indonesia dari data lelang SUN.",
  alternates: {
    canonical: "/",
  },
};

const datasetJsonLd = {
  "@context": "https://schema.org",
  "@type": "Dataset",
  name: "Kurva Yield Obligasi Pemerintah Indonesia",
  description:
    "Imbal hasil lelang Surat Utang Negara (SUN) pemerintah Indonesia per seri dan tenor, disusun dari publikasi DJPPR. Kumpulan data finansial publik untuk observasi pasar obligasi tanpa rekomendasi investasi.",
  url: `${SITE_URL}/`,
  inLanguage: "id-ID",
  keywords: [
    "kurva yield",
    "obligasi pemerintah",
    "indonesia",
    "SUN",
    "lelang surat utang negara",
    "yield",
  ],
  creator: {
    "@type": "Organization",
    name: "Obliq",
    url: SITE_URL,
  },
  temporalCoverage: "2015-05-26/2026-08-04",
  variableMeasured: [
    {
      "@type": "PropertyValue",
      name: "Tenor",
      unitText: "tahun",
    },
    {
      "@type": "PropertyValue",
      name: "Yield",
      unitText: "persen",
    },
  ],
};

export default function HomePage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <JsonLd data={datasetJsonLd} />
      <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">
        Kurva Yield
      </p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Kurva Yield Pemerintah Indonesia
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Imbal hasil lelang SUN terbaru per seri, diurutkan berdasarkan tenor,
        dari publikasi resmi DJPPR.
      </p>

      <ExplainerBox title="Apa itu Obliq?" titleId="apa-itu-obliq-heading">
        <p className="max-w-3xl text-sm leading-relaxed text-ink-muted sm:text-base">
          Obliq adalah kumpulan data pasar surat utang Indonesia — tempat
          pemerintah meminjam uang dan menjanjikan imbalan secara berkala
          sampai jatuh tempo. Data ini disusun dari sumber resmi (DJPPR, BPS,
          BI) dan disajikan dalam bahasa yang mudah dipahami, untuk siapa saja
          yang ingin melihat gambaran pasar ini tanpa perlu jadi ahlinya dulu.
        </p>
        <Link
          href="/belajar"
          className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-ledger-green/30 bg-ledger-green/5 px-3.5 py-1.5 text-sm font-medium text-ledger-green transition-colors hover:border-ledger-green/60 hover:bg-ledger-green/10"
        >
          <BookOpen className="h-4 w-4" aria-hidden />
          Baru di sini? Pelajari dulu istilahnya
        </Link>
      </ExplainerBox>

      <p className="mt-8 text-sm text-ink-muted sm:text-base">
        Di bawah ini kamu bisa lihat data hari ini —
      </p>
      <p className="mt-3 text-sm text-ink-muted sm:text-base">
        Grafik ini menunjukkan berapa persen keuntungan kalau kamu
        &quot;meminjamkan&quot; uang ke pemerintah, untuk berbagai jangka
        waktu.
      </p>
      <div className="mt-3">
        <ChartModal label="Kurva Yield Pemerintah">
          <YieldCurveChart />
        </ChartModal>
      </div>

      <section className="mt-12" aria-labelledby="histori-heading">
        <h2
          id="histori-heading"
          className="font-serif text-xl font-semibold text-ink sm:text-2xl"
        >
          Histori Yield Satu Seri
        </h2>
        <p className="mt-1 text-sm text-ink-muted sm:text-base">
          Yield per tanggal lelang untuk satu seri SUN (mis. FR0100). Rentang
          tanggal tanpa data ditampilkan sebagai garis putus, bukan disambung.
        </p>
        <p className="mt-3 text-sm text-ink-muted sm:text-base">
          Grafik ini menunjukkan bagaimana keuntungan satu seri berubah di
          setiap lelang, dari waktu ke waktu.
        </p>
        <Link
          href="/obligasi/bandingkan"
          className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-ledger-green/30 bg-ledger-green/5 px-3.5 py-1.5 text-sm font-medium text-ledger-green transition-colors hover:border-ledger-green/60 hover:bg-ledger-green/10"
        >
          <GitCompare className="h-4 w-4" aria-hidden />
          Bandingkan yield beberapa seri
        </Link>
        <div className="mt-3">
          <ChartModal label="Histori Yield — Histori Yield Satu Seri">
            <YieldHistoryChart />
          </ChartModal>
        </div>
      </section>
    </section>
  );
}
