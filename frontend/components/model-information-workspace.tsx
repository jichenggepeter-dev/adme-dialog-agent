"use client";

import { CheckCircle, Database, Info, MagnifyingGlass, Stack, Target, Warning } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchEndpoints, fetchStatus } from "@/lib/api";
import type { EndpointMetadata, EndpointOutputType, StatusResponse } from "@/lib/types";
import { registerAssistantCapabilities } from "@/lib/assistant-capabilities";
import type { UIAction } from "@/lib/agent-types";
import { clearHighlight } from "./assistant/assistant-action-transition";
import { useOptionalAssistant } from "@/contexts/assistant-provider";
import { publishAssistantPageContext } from "@/lib/assistant-page-state";

function available(value: string | null | undefined) { return value || "Not reported"; }
function sourceLabel(endpoint: EndpointMetadata) {
  if (!endpoint.source) return "Not verified";
  return [endpoint.source.name, endpoint.source.version ? `v${endpoint.source.version}` : null].filter(Boolean).join(" · ");
}

export function ModelInformationWorkspace() {
  const assistant = useOptionalAssistant();
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointMetadata[]>([]);
  const [registryVersion, setRegistryVersion] = useState<string | null>(null);
  const [compatibilityWarning, setCompatibilityWarning] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [outputType, setOutputType] = useState("all");
  const [metadataStatus, setMetadataStatus] = useState("all");
  const [verifiedUnitOnly, setVerifiedUnitOnly] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [highlightedTarget, setHighlightedTarget] = useState<string | null>(null);
  const detailRef = useRef<HTMLElement>(null);

  useEffect(() => {
    Promise.all([fetchStatus(), fetchEndpoints()]).then(([statusValue, registry]) => {
      setStatus(statusValue);
      const records = Object.values(registry.endpoints);
      setEndpoints(records);
      setRegistryVersion(registry.registry_schema_version);
      setCompatibilityWarning(registry.compatibility_warning);
      setSelectedKey((current) => current ?? records[0]?.raw_key ?? null);
    }).catch(() => setUnavailable(true));
  }, []);

  useEffect(() => {
    if (!endpoints.length) return;
    return registerAssistantCapabilities("/about", { execute(action: UIAction) {
    if (action.type === "OPEN_MODEL_ENDPOINT" || action.type === "SELECT_ENDPOINT") {
      const target = String(action.payload.target ?? "").toLowerCase();
      const endpoint = endpoints.find((item) => item.raw_key.toLowerCase() === target || item.aliases.some((alias) => alias.toLowerCase() === target));
      if (!endpoint) throw new Error("endpoint missing");
      setSearch(""); setCategory("all"); setOutputType("all"); setMetadataStatus("all"); setVerifiedUnitOnly(false);
      setSelectedKey(endpoint.raw_key); setPage(Math.floor(endpoints.indexOf(endpoint) / 12) + 1); setHighlightedTarget(`endpoint-${endpoint.raw_key}`);
      window.requestAnimationFrame(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })); clearHighlight(setHighlightedTarget);
      return { targetId: `endpoint-${endpoint.raw_key}`, message: `Opened ${endpoint.raw_key} metadata` };
    }
    if (action.type === "SET_ABOUT_FILTERS") {
      if (typeof action.payload.category === "string") setCategory(action.payload.category);
      if (typeof action.payload.output_type === "string") setOutputType(action.payload.output_type);
      if (typeof action.payload.metadata_status === "string") setMetadataStatus(action.payload.metadata_status);
      setPage(1); setHighlightedTarget("endpoint-catalog"); clearHighlight(setHighlightedTarget);
      return { targetId: "endpoint-catalog", message: "Endpoint filters applied" };
    }
    throw new Error("unsupported about action");
    }});
  }, [endpoints]);

  const filtered = useMemo(() => endpoints.filter((endpoint) => {
    const query = search.toLowerCase();
    return (!query || `${endpoint.raw_key} ${endpoint.display_name}`.toLowerCase().includes(query))
      && (category === "all" || endpoint.category === category)
      && (outputType === "all" || endpoint.output_type === outputType)
      && (metadataStatus === "all" || endpoint.metadata_status === metadataStatus)
      && (!verifiedUnitOnly || endpoint.unit_verified);
  }), [endpoints, search, category, outputType, metadataStatus, verifiedUnitOnly]);

  const pageSize = 12;
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  const selected = endpoints.find((endpoint) => endpoint.raw_key === selectedKey) ?? null;
  const outputTypes = [...new Set(endpoints.map((endpoint) => endpoint.output_type))] as EndpointOutputType[];

  useEffect(() => publishAssistantPageContext({
    page: "about",
    selected_endpoint: selectedKey,
    active_category: category === "all" ? null : category,
    search_query: search,
    output_type_filter: outputType === "all" ? null : outputType,
    metadata_status_filter: metadataStatus === "all" ? null : metadataStatus,
    verified_unit_only: verifiedUnitOnly,
    current_page: page,
    filtered_endpoint_count: filtered.length,
    visible_endpoints: visible.map((endpoint) => endpoint.raw_key),
  }), [selectedKey, category, search, outputType, metadataStatus, verifiedUnitOnly, page, filtered.length, visible]);

  return <div className={`about-workspace ${assistant?.open && !assistant.closing ? "has-docked-assistant" : ""}`}>
    {unavailable ? <p className="batch-inline-error" role="alert">Backend model information is unavailable. Static scientific boundaries remain visible below.</p> : null}
    {compatibilityWarning ? <p className="mock-warning" role="status">{compatibilityWarning}</p> : null}
    <section className="model-overview" aria-labelledby="model-overview-title">
      <h2 id="model-overview-title">Model Overview</h2>
      <dl>{[
        ["Model Name", status?.model_name], ["Prediction Mode", status?.prediction_mode],
        ["Model Status", status ? status.model_loaded ? "Loaded" : status.predictor_available ? "Not initialized" : "Not available" : null],
        ["Backend Version", status?.backend_version], ["Model Version", status?.model_version],
        ["Registry Schema", registryVersion], ["Execution Environment", status?.execution_environment], ["Input Type", status?.input_type],
      ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{available(value)}</dd></div>)}</dl>
    </section>
    <div className="about-main-grid">
      <section className={`endpoint-catalog ${highlightedTarget === "endpoint-catalog" ? "assistant-target-highlight" : ""}`} aria-labelledby="catalog-title" data-assistant-target="endpoint-catalog">
        <h2 id="catalog-title">Endpoint Catalog</h2>
        <div className="catalog-filters">
          <label className="search-control"><MagnifyingGlass size={17} /><span className="visually-hidden">Search endpoints</span><input placeholder="Search endpoints" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
          <label><span className="visually-hidden">Filter category</span><select value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }}><option value="all">All categories</option>{[...new Set(endpoints.map((endpoint) => endpoint.category))].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select></label>
          <label><span className="visually-hidden">Filter output type</span><select value={outputType} onChange={(event) => { setOutputType(event.target.value); setPage(1); }}><option value="all">All output types</option>{outputTypes.map((value) => <option key={value} value={value}>{endpoints.find((endpoint) => endpoint.output_type === value)?.output_type_label ?? value}</option>)}</select></label>
          <label><span className="visually-hidden">Filter metadata status</span><select value={metadataStatus} onChange={(event) => { setMetadataStatus(event.target.value); setPage(1); }}><option value="all">All metadata states</option><option value="verified">Verified</option><option value="partial">Partial</option><option value="unverified">Unverified</option></select></label>
          <label className="toggle-control"><input type="checkbox" checked={verifiedUnitOnly} onChange={(event) => { setVerifiedUnitOnly(event.target.checked); setPage(1); }} /><span>Verified unit only</span></label>
        </div>
        <div className="table-scroll"><table><thead><tr><th>Endpoint</th><th>Display name</th><th>Category</th><th>Output type</th><th>Unit</th><th>Unit verified</th><th>Metadata</th><th>Source</th><th>Details</th></tr></thead><tbody>{visible.map((endpoint) => <tr key={endpoint.raw_key} className={selectedKey === endpoint.raw_key ? "selected" : ""}><td><code>{endpoint.raw_key}</code></td><td>{endpoint.display_name}</td><td><span className="category-label">{endpoint.category.replaceAll("_", " ")}</span></td><td>{endpoint.output_type_label}</td><td>{endpoint.unit_verified ? endpoint.unit ?? "Unitless" : "—"}</td><td>{endpoint.unit_verified ? "Verified" : "Not verified"}</td><td><span className={`metadata-status metadata-${endpoint.metadata_status}`}>{endpoint.metadata_status}</span></td><td>{sourceLabel(endpoint)}</td><td><button className="table-detail-button" onClick={() => setSelectedKey(endpoint.raw_key)}>Details</button></td></tr>)}</tbody></table></div>
        <footer className="table-pagination"><span>Showing {visible.length} of {filtered.length} endpoints</span><div><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}>‹</button><span>Page {page} of {pageCount}</span><button disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>›</button></div></footer>
      </section>
      <section ref={detailRef} className={`endpoint-detail-panel ${highlightedTarget?.startsWith("endpoint-") ? "assistant-target-highlight" : ""}`} aria-live="polite" data-assistant-target={selected ? `endpoint-${selected.raw_key}` : undefined}>
        <h2>Endpoint Details</h2>
        {selected ? <dl>{[
          ["Raw Endpoint Name", selected.raw_key], ["Aliases", selected.aliases.length ? selected.aliases.join(", ") : "None documented"],
          ["Display Name", selected.display_name], ["Category", selected.category.replaceAll("_", " ")],
          ["Output Type", selected.output_type_label], ["Prediction Task", selected.prediction_task],
          ["Positive Class", selected.positive_class], ["Unit", selected.unit_verified ? selected.unit ?? "Unitless" : "Not verified"],
          ["Directionality", selected.directionality], ["Description", selected.description],
          ["Interpretation Limitation", selected.interpretation_limitations], ["Source", sourceLabel(selected)],
          ["Source Reference", selected.source?.reference], ["ADMET-AI Compatibility", selected.compatible_admet_ai_versions.join(", ")],
          ["Metadata Status", selected.metadata_status],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{available(value)}</dd></div>)}</dl> : <p>Select an endpoint to inspect registry metadata.</p>}
      </section>
      <aside className="about-rail">
        <section><h2><Stack size={23} weight="duotone" />Prediction Modes</h2><div className={`mode-explanation ${status?.prediction_mode === "mock" ? "active" : ""}`}><b>Mock Mode</b><p>Deterministic interface fixtures, not ADMET-AI predictions.</p></div><div className={`mode-explanation ${status?.prediction_mode === "real" ? "active" : ""}`}><b>Real ADMET-AI</b><p>Locally installed computational model; outputs still require validation.</p></div></section>
        <section><h2><Target size={23} weight="duotone" />Scientific Scope</h2><ul className="icon-list">{["Prioritization and exploration only", "Not experimental measurements", "Not clinical conclusions", "Not regulatory evidence", "Requires experimental validation"].map((item) => <li key={item}><CheckCircle size={16} />{item}</li>)}</ul></section>
        <section><h2><Database size={23} weight="duotone" />Data Sources</h2><dl className="source-list"><div><dt>ADMET-AI 2.x</dt><dd>Prediction tasks, units, and DrugBank percentiles</dd></div><div><dt>RDKit</dt><dd>Calculated descriptors, counts, rules, and structure alerts</dd></div><div><dt>TDC task references</dt><dd>Linked scientific task definitions requiring endpoint-specific review</dd></div></dl></section>
        <section><h2><Warning size={23} weight="duotone" />Known Limitations</h2><ul className="limitations-list">{["Partial metadata does not imply fully verified endpoint semantics.", "Percentile direction is not a quality ranking.", "Model probabilities are not clinical risks.", "Results vary with model and dependency versions.", "Unknown fields remain visible and uninterpreted."].map((item) => <li key={item}><Info size={15} />{item}</li>)}</ul></section>
      </aside>
    </div>
    <footer className="about-metadata-footer"><span><b>Model version</b>{available(status?.model_version)}</span><span><b>Prediction mode</b>{available(status?.prediction_mode)}</span><span><b>Registry schema</b>{available(registryVersion)}</span><span><b>Endpoints</b>{endpoints.length}</span><p><Info size={18} /> Computational predictions and relative percentiles require experimental and scientific validation.</p></footer>
  </div>;
}
