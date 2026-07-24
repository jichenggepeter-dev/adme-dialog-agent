import type { PageContext } from "./agent-types";

let current: PageContext | null = null;

export function publishAssistantPageContext(value: PageContext): () => void {
  current = value;
  return () => { if (current === value) current = null; };
}

export function getAssistantPageContext(fallback: PageContext): PageContext {
  if (!current) return fallback;
  if (current.page === "batch" && fallback.page === "batch") {
    return { ...fallback, ...current, batch_job_id: current.batch_job_id || fallback.batch_job_id || null };
  }
  return current.page === fallback.page ? current : fallback;
}
