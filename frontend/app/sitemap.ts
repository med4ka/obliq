import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

/**
 * Basic sitemap for the static routes. The yield curve page is the most stable
 * dataset (updated on the backend scheduler), so it gets the highest priority.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  return [
    {
      url: SITE_URL,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE_URL}/saham`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/makro`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/belajar`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.4,
    },
    {
      url: `${SITE_URL}/bandingkan`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
  ];
}