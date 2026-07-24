import type { ClientError, JsonValue } from "./types";

const numberFormatter = new Intl.NumberFormat("en-US", {
  maximumSignificantDigits: 5,
});

export function formatPropertyName(key: string): string {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatValue(value: JsonValue): string {
  if (value === null) return "Not available";
  if (typeof value === "number") return numberFormatter.format(value);
  if (typeof value === "boolean") return value ? "True" : "False";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function messageForError(error: ClientError): string {
  const messages: Record<string, string> = {
    INVALID_SMILES: "The backend could not parse this SMILES string. Check the syntax and try again.",
    MODEL_NOT_AVAILABLE: "The real ADMET model is not installed in the backend environment.",
    MODEL_LOAD_FAILED: "The real ADMET model could not be initialized. Review the backend log for details.",
    PREDICTION_FAILED: "Prediction did not complete. Review the backend log, then try again when ready.",
    INVALID_REQUEST: "The request was incomplete. Check the input and try again.",
    BACKEND_UNAVAILABLE: "The FastAPI service is not reachable. Start the backend and refresh its status.",
    REQUEST_TIMEOUT: "The prediction timed out. The first real-model run may need longer to initialize.",
    COMPOUND_NOT_FOUND: "No matching compound was found. Refine the name or use a PubChem CID.",
    COMPOUND_AMBIGUOUS: "Multiple compounds matched this query. Refine the name or use a PubChem CID.",
    PUBCHEM_UNAVAILABLE: "Compound metadata could not be retrieved from PubChem. Try a SMILES string instead.",
  };
  return messages[error.code] ?? error.message;
}
