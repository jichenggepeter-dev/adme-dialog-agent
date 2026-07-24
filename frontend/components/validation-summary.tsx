import { CheckCircle, Copy, FileText, Prohibit, Question, Warning } from "@phosphor-icons/react";
import type { BatchValidationSummary } from "@/lib/types";

const METRICS = [
  ["total_rows", "Total rows", FileText], ["valid_molecules", "Valid molecules", CheckCircle], ["invalid_smiles", "Invalid SMILES", Warning],
  ["missing_smiles", "Missing SMILES", Question], ["duplicate_molecules", "Duplicate molecules", Copy], ["unique_valid_molecules", "Unique valid molecules", Prohibit],
] as const;
export function ValidationSummary({ summary }: { summary: BatchValidationSummary }) {
  return <div className="validation-metrics" aria-label="Validation summary">{METRICS.map(([key, label, Icon]) => <div key={key}><Icon size={26} weight="duotone" aria-hidden="true" /><span><small>{label}</small><strong>{summary[key].toLocaleString()}</strong></span></div>)}</div>;
}
