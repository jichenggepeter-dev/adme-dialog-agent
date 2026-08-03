"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createAgentSession, decideConfirmation, decidePendingAction, getPredictionResource, streamAgentMessage, AgentApiError } from "@/lib/agent-api";
import type { AgentMessage, AgentResponse, AgentStreamEvent, AssistantStreamStatus, Confirmation, PageContext, PendingAction, StructuredPayload, ToolActivity } from "@/lib/agent-types";
import { applyStreamEvent, finalizeStreamedMessage } from "@/lib/assistant-stream-state";
import { getAssistantPageContext } from "@/lib/assistant-page-state";
import { executeUIAction, shouldCollapseForAction, type UIActionExecutionResult } from "@/lib/ui-action-dispatcher";
import { transitionDelay, type ActionPhase } from "@/components/assistant/assistant-action-transition";
import type { PredictionResponse } from "@/lib/types";

export type ViewMessage = AgentMessage & { payloads?: StructuredPayload[]; tools?: ToolActivity[] };
type AssistantState = { open: boolean; closing: boolean; ready: boolean; loading: boolean; messages: ViewMessage[]; pending: Confirmation | null; pendingAction: PendingAction | null; error: AgentApiError | null; stateVersion: number; streamStatus: AssistantStreamStatus; actionPhase: ActionPhase; actionResult: UIActionExecutionResult | null; guidedMode: boolean; guidedPrediction: PredictionResponse | null; send: (text: string) => Promise<void>; cancelStream: () => void; decide: (decision: "approve" | "reject") => Promise<void>; decideAction: (decision: "approve" | "reject") => Promise<void>; setOpen: (value: boolean) => void; exitGuidedMode: () => void; clearError: () => void };
const Context = createContext<AssistantState | null>(null);

function routeContext(pathname: string): PageContext {
  if (pathname.startsWith("/batch")) return { page: "batch", batch_job_id: pathname.split("/")[2] || null, selected_compound_ids: [], selected_row_numbers: [], selected_endpoints: [] };
  if (pathname.startsWith("/about")) return { page: "about" };
  return { page: "single" };
}

export function AssistantProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter();
  const [open, setOpenState] = useState(false); const [closing, setClosing] = useState(false); const [ready, setReady] = useState(false); const [loading, setLoading] = useState(false);
  const openRef = useRef(false); const closeTimerRef = useRef<number | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null); const [stateVersion, setStateVersion] = useState(0);
  const [messages, setMessages] = useState<ViewMessage[]>([]); const [pending, setPending] = useState<Confirmation | null>(null); const [error, setError] = useState<AgentApiError | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [streamStatus, setStreamStatus] = useState<AssistantStreamStatus>("idle");
  const streamAbortRef = useRef<AbortController | null>(null);
  const [actionPhase, setActionPhase] = useState<ActionPhase>("idle"); const [actionResult, setActionResult] = useState<UIActionExecutionResult | null>(null);
  const [guidedMode, setGuidedMode] = useState(false); const [guidedPrediction, setGuidedPrediction] = useState<PredictionResponse | null>(null);

  const setOpen = useCallback((value: boolean) => {
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
    if (value) {
      openRef.current = true; setClosing(false); setOpenState(true); return;
    }
    if (!openRef.current) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) { openRef.current = false; setClosing(false); setOpenState(false); return; }
    setClosing(true);
    closeTimerRef.current = window.setTimeout(() => {
      openRef.current = false; setClosing(false); setOpenState(false); closeTimerRef.current = null;
    }, 580);
  }, []);

  useEffect(() => () => { if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current); }, []);
  useEffect(() => () => streamAbortRef.current?.abort(), []);

  useEffect(() => { let active = true; (async () => {
    try {
      const session = await createAgentSession();
      if (!active) return;
      setSessionId(session.session_id);
      setStateVersion(session.state_version);
      setMessages([]);
    } catch (caught) { if (active) setError(caught instanceof AgentApiError ? caught : new AgentApiError("AGENT_OFFLINE", "The Assistant is unavailable.")); }
    finally { if (active) setReady(true); }
  })(); return () => { active = false; }; }, []);
  useEffect(() => {
    document.body.classList.toggle("assistant-docked-active", open && !closing);
    return () => document.body.classList.remove("assistant-docked-active");
  }, [closing, open, pathname]);

  const ingest = useCallback(async (response: AgentResponse, replaceStreamedMessage = false) => {
    setStateVersion(response.state_version); setPending(response.pending_confirmation); setPendingAction(response.pending_action);
    setMessages((items) => replaceStreamedMessage
      ? finalizeStreamedMessage(items, sessionId ?? "", response)
      : [...items, { message_id: response.message_id, session_id: sessionId ?? "", role: "assistant", content: response.text, created_at: new Date().toISOString(), metadata: {}, payloads: response.structured_payloads, tools: response.tool_activity }]);
    if (!sessionId) return;
    if (response.pending_confirmation) {
      setActionPhase("collapsing_for_action"); setOpen(false);
      await transitionDelay("collapse");
      setGuidedMode(true); setGuidedPrediction(null);
      setActionPhase("idle");
      if (!pathname.startsWith("/single")) router.push("/single");
    }
    const predictionPayload = response.structured_payloads.find((item) => item.type === "prediction");
    const predictionResourceId = predictionPayload?.data.prediction_resource_id;
    if (typeof predictionResourceId === "string") {
      setOpen(false); await transitionDelay("collapse"); setGuidedMode(true);
      if (!pathname.startsWith("/single")) router.push("/single");
      setGuidedPrediction(await getPredictionResource(sessionId, predictionResourceId));
    }
    for (const action of response.ui_action_proposals) {
      setActionResult(null); setActionPhase("preparing_action");
      if (shouldCollapseForAction(action)) { setActionPhase("collapsing_for_action"); await transitionDelay("contentFade"); setOpen(false); await transitionDelay("collapse"); }
      setActionPhase("executing_action");
      const result = await executeUIAction(action, { sessionId, stateVersion: response.state_version, currentRoute: pathname, navigate: router.push });
      setActionResult(result);
      if (result.ok) { setActionPhase(result.target ? "highlighting_target" : "action_completed"); if (result.target) await transitionDelay("highlight"); setActionPhase("action_completed"); await transitionDelay("completed"); setActionPhase("idle"); }
      else { setActionPhase("action_failed"); setOpen(true); }
    }
  }, [pathname, router, sessionId, setOpen]);

  const send = useCallback(async (text: string) => { if (!sessionId || loading || !text.trim()) return; setLoading(true); setError(null); setStreamStatus("connecting");
    setMessages((items) => [...items, { message_id: crypto.randomUUID(), session_id: sessionId, role: "user", content: text.trim(), created_at: new Date().toISOString(), metadata: {} }]);
    const controller = new AbortController();
    streamAbortRef.current = controller;
    try {
      const fallback = routeContext(window.location.pathname);
      const pageContext = getAssistantPageContext(fallback);
      const onEvent = (event: AgentStreamEvent) => {
        setMessages((items) => applyStreamEvent(items, event));
        if (event.type === "tool_started" || event.type === "tool_completed") setStreamStatus("tool");
        else if (event.type === "confirmation_required") setStreamStatus("waiting_confirmation");
        else if (event.type === "error") setStreamStatus("failed");
        else if (event.type === "response_completed") setStreamStatus("completed");
        else setStreamStatus("generating");
      };
      const response = await streamAgentMessage(sessionId, text.trim(), stateVersion, pageContext, { signal: controller.signal, onEvent });
      await ingest(response, true);
      setStreamStatus(response.pending_confirmation || response.pending_action ? "waiting_confirmation" : "completed");
    } catch (caught) { setStreamStatus("failed"); setError(caught instanceof AgentApiError ? caught : new AgentApiError("AGENT_ERROR", "The Assistant request failed.")); } finally { streamAbortRef.current = null; setLoading(false); }
  }, [ingest, loading, sessionId, stateVersion]);

  const cancelStream = useCallback(() => { streamAbortRef.current?.abort(); }, []);

  const decide = useCallback(async (decision: "approve" | "reject") => { if (!sessionId || !pending || loading) return; setLoading(true); setError(null);
    try { await ingest(await decideConfirmation(sessionId, pending.confirmation_id, decision, stateVersion)); setStreamStatus("completed"); if (decision === "reject") setGuidedMode(false); } catch (caught) { setStreamStatus("failed"); setError(caught instanceof AgentApiError ? caught : new AgentApiError("AGENT_ERROR", "Confirmation failed.")); } finally { setLoading(false); }
  }, [ingest, loading, pending, sessionId, stateVersion]);

  const decideAction = useCallback(async (decision: "approve" | "reject") => { if (!sessionId || !pendingAction || loading) return; setLoading(true); setError(null);
    try {
      const response = await decidePendingAction(sessionId, pendingAction.action_id, decision, stateVersion);
      await ingest(response);
      setStreamStatus("completed");
      if (decision === "approve" && pendingAction.action_type === "run_batch_job") {
        const jobId = response.structured_payloads.find((item) => item.type === "batch_summary")?.data.job_id;
        if (typeof jobId === "string" && jobId) router.push(`/batch/${encodeURIComponent(jobId)}`);
      }
    } catch (caught) { setStreamStatus("failed"); setError(caught instanceof AgentApiError ? caught : new AgentApiError("AGENT_ERROR", "Batch action confirmation failed.")); } finally { setLoading(false); }
  }, [ingest, loading, pendingAction, router, sessionId, stateVersion]);

  const value = useMemo(() => ({ open, closing, ready, loading, messages, pending, pendingAction, error, stateVersion, streamStatus, actionPhase, actionResult, guidedMode, guidedPrediction, send, cancelStream, decide, decideAction, setOpen, exitGuidedMode: () => setGuidedMode(false), clearError: () => setError(null) }), [open, closing, ready, loading, messages, pending, pendingAction, error, stateVersion, streamStatus, actionPhase, actionResult, guidedMode, guidedPrediction, send, cancelStream, decide, decideAction, setOpen]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useAssistant() { const value = useContext(Context); if (!value) throw new Error("useAssistant must be inside AssistantProvider"); return value; }
export function useOptionalAssistant() { return useContext(Context); }
