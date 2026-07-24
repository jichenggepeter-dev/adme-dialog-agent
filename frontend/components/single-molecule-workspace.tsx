"use client";

import { Flask, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiClientError, fetchEndpoints, fetchStatus, predictSmiles, resolveCompound } from "@/lib/api";
import { messageForError } from "@/lib/formatters";
import type { CompoundResponse, EndpointMetadata, PredictionResponse, StatusResponse } from "@/lib/types";
import { CompoundConfirmationCard } from "./compound-confirmation-card";
import { CompoundSearchForm } from "./compound-search-form";
import { PredictionResults } from "./prediction-results";
import { PredictionStatusBar } from "./prediction-status-bar";
import { registerAssistantCapabilities } from "@/lib/assistant-capabilities";
import type { UIAction } from "@/lib/agent-types";
import { clearHighlight } from "./assistant/assistant-action-transition";
import { AssistantGuidedWorkspace } from "./assistant/assistant-guided-workspace";
import { useAssistant } from "@/contexts/assistant-provider";
import { publishAssistantPageContext } from "@/lib/assistant-page-state";

export function SingleMoleculeWorkspace() {
  const { open: assistantOpen, closing: assistantClosing, guidedMode, guidedPrediction, loading, pending } = useAssistant();
  const [query, setQuery] = useState("");
  const [compound, setCompound] = useState<CompoundResponse | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [registry, setRegistry] = useState<Record<string, EndpointMetadata>>({});
  const [resolving, setResolving] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [resolutionError, setResolutionError] = useState<string | null>(null);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [lastPrediction, setLastPrediction] = useState<Date | null>(null);
  const [highlightedTarget, setHighlightedTarget] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const categoryRefs = useRef<Record<string, HTMLElement | null>>({});

  const refreshStatus = useCallback(async () => {
    try { setStatus(await fetchStatus()); } catch { setStatus(null); }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.allSettled([fetchStatus(), fetchEndpoints()]).then(([statusResult, endpointResult]) => {
      if (!active) return;
      if (statusResult.status === "fulfilled") setStatus(statusResult.value);
      if (endpointResult.status === "fulfilled") setRegistry(endpointResult.value.endpoints);
    });
    return () => { active = false; };
  }, []);

  const currentResult = guidedPrediction ?? result;
  useEffect(() => publishAssistantPageContext({
    page: "single",
    compound_id: typeof pending?.payload.compound_id === "string" ? pending.payload.compound_id : null,
    prediction_id: null,
    active_view: currentResult ? "prediction_results" : (compound || pending ? "structure_review" : "input"),
    compound_query: query,
    compound_name: compound?.preferred_name ?? (typeof pending?.payload.preferred_name === "string" ? pending.payload.preferred_name : null),
    canonical_smiles: currentResult?.canonical_smiles ?? compound?.canonical_smiles ?? pending?.canonical_smiles ?? null,
    result_available: Boolean(currentResult),
    result_categories: currentResult ? Object.entries(currentResult.predictions).filter(([, values]) => Object.keys(values).length > 0).map(([category]) => category) : [],
    prediction_mode: currentResult?.prediction_mode ?? null,
  }), [compound, currentResult, pending, query]);

  useEffect(() => registerAssistantCapabilities("/single", { execute(action: UIAction) {
    if (action.type === "SET_COMPOUND_INPUT") {
      const value = String(action.payload.value ?? ""); if (!value) throw new Error("missing value");
      setQuery(value); setResolutionError(null); setHighlightedTarget("compound-input");
      if (action.payload.focus !== false) inputRef.current?.focus();
      clearHighlight(setHighlightedTarget); return { targetId: "compound-input", message: "Input updated" };
    }
    if (action.type === "FOCUS_COMPOUND_INPUT") { inputRef.current?.focus(); setHighlightedTarget("compound-input"); clearHighlight(setHighlightedTarget); return { targetId: "compound-input", message: "Input focused" }; }
    if (action.type === "FOCUS_RESULT_SECTION") {
      const target = String(action.payload.target ?? "").toLowerCase();
      const element = categoryRefs.current[target];
      if (!element) throw new Error("result unavailable");
      setHighlightedTarget(target); element.scrollIntoView({ behavior: "smooth", block: "center" }); clearHighlight(setHighlightedTarget);
      return { targetId: `${target}-section`, message: `Focused ${target} results` };
    }
    throw new Error("unsupported single action");
  }}), [result]);

  async function handleResolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim() || resolving) return;
    setResolving(true);
    setResolutionError(null);
    setPredictionError(null);
    setResult(null);
    try {
      setCompound(await resolveCompound(query.trim()));
    } catch (caught) {
      const error = caught instanceof ApiClientError ? caught : new ApiClientError("INTERNAL_ERROR", "Compound resolution did not complete.");
      setCompound(null);
      setResolutionError(messageForError(error));
    } finally {
      setResolving(false);
    }
  }

  async function runPrediction() {
    if (!compound || predicting) return;
    setPredicting(true);
    setPredictionError(null);
    try {
      setResult(await predictSmiles(compound.canonical_smiles));
      setLastPrediction(new Date());
      void refreshStatus();
    } catch (caught) {
      const error = caught instanceof ApiClientError ? caught : new ApiClientError("INTERNAL_ERROR", "Prediction did not complete.");
      setPredictionError(messageForError(error));
    } finally {
      setPredicting(false);
    }
  }

  function changeCompound() {
    setCompound(null);
    setResult(null);
    setPredictionError(null);
  }

  return (
    <div className={`single-workspace ${guidedMode ? "is-assistant-guided" : ""} ${assistantOpen && !assistantClosing && !guidedMode ? "has-docked-assistant" : ""}`}>
      <aside className="compound-column">
        {guidedMode ? <AssistantGuidedWorkspace /> : <><CompoundSearchForm inputRef={inputRef} highlighted={highlightedTarget === "compound-input"} value={query} loading={resolving} error={resolutionError} onChange={(value) => { setQuery(value); setResolutionError(null); }} onSubmit={handleResolve} />
        {compound ? <CompoundConfirmationCard compound={compound} predicting={predicting} onPredict={() => void runPrediction()} onChangeCompound={changeCompound} /> : null}</>}
      </aside>
      <section className="prediction-column" aria-label="Prediction workspace">
        <PredictionStatusBar status={status} lastPrediction={lastPrediction} />
        {predictionError ? <div className="prediction-error" role="alert"><WarningCircle size={20} aria-hidden="true" /><div><strong>Prediction did not complete</strong><p>{predictionError}</p></div></div> : null}
        {predicting || (guidedMode && loading && !guidedPrediction) ? <div className="prediction-loading" role="status"><Flask size={34} weight="duotone" aria-hidden="true" /><div><h2>Running ADME/ADMET prediction</h2><p>The first real-model prediction may take longer while the model initializes.</p></div></div> : guidedPrediction || result ? <PredictionResults result={guidedPrediction ?? result!} endpointRegistry={registry} highlightedCategory={highlightedTarget} onCategoryElement={(category, element) => { categoryRefs.current[category] = element; }} /> : <div className="prediction-empty"><Flask size={42} weight="duotone" aria-hidden="true" /><h2>{guidedMode ? "Waiting for structure confirmation" : "Ready for a confirmed compound"}</h2><p>{guidedMode ? "Confirm the resolved structure in the guided workflow to run the computational prediction." : "Resolve and confirm a compound on the left, then run ADME/ADMET prediction."}</p></div>}
      </section>
    </div>
  );
}
