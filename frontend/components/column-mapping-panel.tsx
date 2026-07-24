"use client";

import type { BatchColumnMapping, BatchUploadResponse } from "@/lib/types";

const FIELDS: { key: keyof BatchColumnMapping; label: string; required: boolean }[] = [
  { key: "smiles", label: "SMILES column", required: true }, { key: "compound_id", label: "Compound ID column", required: false }, { key: "compound_name", label: "Compound name column", required: false },
];

export function ColumnMappingPanel({ upload, mapping, error, busy, onChange, onContinue, onReplace }: { upload: BatchUploadResponse; mapping: BatchColumnMapping; error: string | null; busy: boolean; onChange: (mapping: BatchColumnMapping) => void; onContinue: () => void; onReplace: () => void }) {
  return <section className="batch-stage-panel" aria-labelledby="mapping-title">
    <header><div><span className="stage-kicker">Step 2</span><h2 id="mapping-title">Map source columns</h2><p><b>{upload.source_filename}</b> · {upload.row_count.toLocaleString()} rows · {upload.file_type.toUpperCase()}</p></div></header>
    <div className="mapping-grid">{FIELDS.map((field) => <label key={field.key}>{field.label}{field.required ? " *" : ""}<select value={mapping[field.key] ?? ""} onChange={(event) => onChange({ ...mapping, [field.key]: event.target.value || null })}><option value="">{field.required ? "Select a column" : "Not mapped"}</option>{upload.columns.map((column) => <option key={column} value={column} disabled={Object.entries(mapping).some(([key, value]) => key !== field.key && value === column)}>{column}</option>)}</select></label>)}</div>
    <div className="table-scroll mapping-preview"><table><caption>Uploaded data preview</caption><thead><tr>{upload.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{upload.preview.slice(0, 5).map((row, index) => <tr key={index}>{upload.columns.map((column) => <td key={column}><code>{row[column] || "—"}</code></td>)}</tr>)}</tbody></table></div>
    {error ? <p className="batch-inline-error" role="alert">{error}</p> : null}
    <div className="stage-actions"><button className="secondary-action" onClick={onReplace}>Replace file</button><button className="primary-action" disabled={!mapping.smiles || busy} onClick={onContinue}>{busy ? "Validating rows..." : "Validate dataset"}</button></div>
  </section>;
}
