/**
 * Site constants shared across metadata, sitemap, robots, and JSON-LD.
 *
 * SITE_URL is the canonical base URL. Override with NEXT_PUBLIC_SITE_URL
 * (e.g. for production); the dev default keeps links/OG/sitemap valid locally.
 * Must not end with a trailing slash.
 */
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"
).replace(/\/+$/, "");

export const SITE_NAME = "Obliq";

export const SITE_DESCRIPTION =
  "Kurva yield obligasi pemerintah Indonesia dan indikator makro, disusun dari data lelang SUN (DJPPR), BPS, dan BI.";