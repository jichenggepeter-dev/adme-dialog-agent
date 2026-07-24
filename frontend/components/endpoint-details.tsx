import { Info } from "@phosphor-icons/react";
import type { EndpointMetadata, JsonValue, PredictionCategoryName } from "@/lib/types";
import { formatPropertyName, formatValue } from "@/lib/formatters";

export function EndpointDetails({ rawKey, value, category, metadata }: { rawKey: string; value: JsonValue; category: PredictionCategoryName; metadata?: EndpointMetadata }) {
  const displayName = metadata?.display_name ?? formatPropertyName(rawKey);
  return (
    <details className="endpoint-row">
      <summary>
        <span className="endpoint-name"><b>{displayName}</b><code>{rawKey}</code></span>
        <span className="endpoint-output-type">{metadata?.output_type_label ?? "Metadata not verified"}</span>
        <span className="endpoint-value">{formatValue(value)}{metadata?.unit_verified && metadata.unit ? ` ${metadata.unit}` : ""}</span>
        <Info size={15} aria-hidden="true" />
      </summary>
      <div className="endpoint-detail-body">
        <dl>
          <div><dt>Raw model key</dt><dd><code>{rawKey}</code></dd></div>
          <div><dt>Category</dt><dd>{category}</dd></div>
          <div><dt>Output type</dt><dd>{metadata?.output_type_label ?? "Metadata not verified"}</dd></div>
          <div><dt>Verified unit</dt><dd>{metadata?.unit_verified ? metadata.unit ?? "Unitless" : "Not verified"}</dd></div>
          <div><dt>Metadata status</dt><dd>{metadata?.metadata_status ?? "unverified"}</dd></div>
        </dl>
        <p>{metadata?.description ?? "No verified endpoint description is available."}</p>
        <p className="metadata-boundary">{metadata?.interpretation_limitations ?? "Interpretation metadata has not been verified for this endpoint."}</p>
      </div>
    </details>
  );
}
