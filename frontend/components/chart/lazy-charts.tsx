"use client";

/**
 * Client-only lazy loaders for every chart (Sesi 25 requirement): all charts
 * are loaded with next/dynamic + ssr:false so Recharts never inflates the
 * initial JS of a page (Sesi 24 measured ~135 KB gzip baseline; Recharts adds
 * ~80-100 KB gzip if loaded eagerly). Each shows the ChartSkeleton while the
 * chunk loads.
 *
 * Server pages import from here (this file is the client boundary).
 */
import dynamic from "next/dynamic";

import ChartSkeleton from "@/components/chart-skeleton";

const Skeleton = () => <ChartSkeleton />;

export const YieldCurveChart = dynamic(
  () => import("./yield-curve-chart"),
  { ssr: false, loading: Skeleton }
);

export const YieldHistoryChart = dynamic(
  () => import("./yield-history-chart"),
  { ssr: false, loading: Skeleton }
);

export const MacroChart = dynamic(
  () => import("./macro-chart"),
  { ssr: false, loading: Skeleton }
);

export const IhsgChart = dynamic(
  () => import("./ihsg-chart"),
  { ssr: false, loading: Skeleton }
);

export const StockChart = dynamic(
  () => import("./stock-chart"),
  { ssr: false, loading: Skeleton }
);

export const StockCompareChart = dynamic(
  () => import("./stock-compare-chart"),
  { ssr: false, loading: Skeleton }
);

export const BondCompareChart = dynamic(
  () => import("./bond-compare-chart"),
  { ssr: false, loading: Skeleton }
);

export const MacroBarChart = dynamic(
  () => import("./macro-bar-chart"),
  { ssr: false, loading: Skeleton }
);