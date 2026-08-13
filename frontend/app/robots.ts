import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/**
 * Public site — allow all crawlers; point them at the sitemap. No private
 * sections exist yet (no auth in Phase 1-3, ARCHITECTURE.md §5).
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}