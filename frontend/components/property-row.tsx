import { formatPropertyName, formatValue } from "@/lib/formatters";
import type { JsonValue } from "@/lib/types";

export function PropertyRow({ name, value }: { name: string; value: JsonValue }) {
  return (
    <div className="property-row">
      <dt title={name}>{formatPropertyName(name)}</dt>
      <dd title={typeof value === "object" ? JSON.stringify(value) : String(value)}>{formatValue(value)}</dd>
    </div>
  );
}
