import { Flask } from "@phosphor-icons/react/dist/ssr";
import { REVIEW_MODE, reviewRevision } from "@/lib/review-mode";

export function ReviewModeBanner({
  enabled = REVIEW_MODE,
  revision = reviewRevision(),
}: {
  enabled?: boolean;
  revision?: string;
}) {
  if (!enabled) return null;

  return (
    <aside className="review-mode-banner" aria-label="Review application status">
      <div>
        <Flask size={17} weight="fill" aria-hidden="true" />
        <strong>PR Preview · Mock Agent v1</strong>
        <span>Deterministic test behavior · temporary synthetic state · not scientific conclusions</span>
        <code>revision {revision}</code>
      </div>
    </aside>
  );
}
