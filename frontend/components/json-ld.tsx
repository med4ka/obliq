/**
 * Pass a plain object; serialized exactly once (no double-encoding —
 * dangerouslySetInnerHTML only runs with a serialized string).
 */
export default function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}