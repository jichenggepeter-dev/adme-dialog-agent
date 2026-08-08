import type { AgentActivityItem } from "@/lib/agent-types";

const TOOL_LABELS: Record<string, string> = {
  resolve_compound: "Resolve compound",
  get_compound_context: "Check structure",
  predict_single_compound: "Run ADME prediction",
  explain_endpoint: "Load endpoint metadata",
  search_adme_evidence: "Search ADME evidence",
  get_model_information: "Read model information",
  get_batch_job_status: "Read batch status",
  get_batch_errors: "Check batch issues",
  summarize_batch_results: "Summarize batch results",
  get_batch_rows: "Read batch rows",
  compare_batch_rows: "Compare batch rows",
  prepare_batch_action: "Prepare batch action",
  compare_compounds: "Compare compounds",
};

const STATUS_LABELS: Record<AgentActivityItem["status"], string> = {
  started: "In progress",
  completed: "Completed",
  waiting: "Waiting",
  supported: "Supported",
  partial: "Partially supported",
  conflicting: "Conflicting evidence",
  no_evidence: "No evidence found",
  prohibited: "Unavailable",
  stale_only: "Older evidence only",
  error: "Error",
  blocked: "Blocked",
};

const RECOVERY_LABELS: Record<NonNullable<AgentActivityItem["recovery"]>, string> = {
  edit_and_retry: "Edit your request and try again.",
  review_error: "Review the error code before trying again.",
  review_confirmation: "Review the proposed action, then approve or reject it.",
  refine_question: "Refine the question or ask for a different evidence source.",
};

function activityLabel(item: AgentActivityItem): string {
  if (item.kind === "request") return "Response stream active";
  if (item.kind === "tool") return TOOL_LABELS[item.tool_name ?? ""] ?? "Use scientific tool";
  if (item.kind === "confirmation") return "Confirmation required";
  if (item.kind === "evidence") return item.source_title ?? "Evidence source";
  if (item.kind === "unknown") return "Evidence result";
  if (item.kind === "error") return "Request stopped";
  return "Response completed";
}

function safeSourceUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

function displayTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf())
    ? "Time unavailable"
    : parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function ActivityTrace({
  items,
  onReturnToComposer,
}: {
  items: AgentActivityItem[];
  onReturnToComposer?: () => void;
}) {
  if (items.length === 0) return null;
  const correlationId = items.at(-1)?.correlation_id;

  return (
    <details className="agent-activity-trace">
      <summary aria-label={`Activity and evidence trace for response ${correlationId ?? "unknown"}`}>
        <span>Activity &amp; evidence trace</span>
        <small>{items.length} {items.length === 1 ? "step" : "steps"}</small>
      </summary>
      {correlationId ? <p className="activity-correlation">Correlation: <code>{correlationId}</code></p> : null}
      <ol aria-label="Agent activity trace">
        {items.map((item) => {
          const sourceUrl = safeSourceUrl(item.source_url);
          return <li key={item.id} className={`activity-${item.status}`}>
            <div>
              <strong>{activityLabel(item)}</strong>
              <span className="activity-status">{STATUS_LABELS[item.status]}</span>
            </div>
            <div className="activity-meta">
              <time dateTime={item.occurred_at}>{displayTime(item.occurred_at)}</time>
              {item.duration_ms == null ? null : <span>{item.duration_ms} ms</span>}
              {item.error_code ? <code>{item.error_code}</code> : null}
            </div>
            {sourceUrl ? (
              <a href={sourceUrl} target="_blank" rel="noreferrer" aria-label={`Open source: ${item.source_title ?? "Evidence source"} (opens in new tab)`}>
                Open source
              </a>
            ) : null}
            {item.recovery ? <p className="activity-recovery">Next: {RECOVERY_LABELS[item.recovery]}</p> : null}
            {item.recovery && onReturnToComposer ? <button type="button" className="activity-recovery-action" onClick={onReturnToComposer}>Return to message box</button> : null}
          </li>;
        })}
      </ol>
    </details>
  );
}
