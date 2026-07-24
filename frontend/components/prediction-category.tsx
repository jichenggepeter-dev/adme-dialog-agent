import { ArrowDown, ArrowsOutCardinal, ChartBar, Drop, Flask, Hexagon, ShieldWarning, Sparkle, Wind } from "@phosphor-icons/react";
import { CATEGORY_LABELS } from "@/lib/constants";
import type { EndpointMetadata, JsonValue, PredictionCategoryName } from "@/lib/types";
import type { Ref } from "react";
import { EndpointDetails } from "./endpoint-details";

const ICONS = {
  absorption: ArrowDown,
  distribution: ArrowsOutCardinal,
  metabolism: Flask,
  excretion: Wind,
  toxicity: ShieldWarning,
  physicochemical: Hexagon,
  drug_likeness: Sparkle,
  benchmark: ChartBar,
  other: Drop,
};

export function PredictionCategory({ category, values, totalCount, endpointRegistry = {}, highlighted = false, sectionRef }: { category: PredictionCategoryName; values: Record<string, JsonValue>; totalCount?: number; endpointRegistry?: Record<string, EndpointMetadata>; highlighted?: boolean; sectionRef?: Ref<HTMLElement> }) {
  const entries = Object.entries(values);
  const Icon = ICONS[category];
  return (
    <section ref={sectionRef} className={`prediction-category-card ${highlighted ? "assistant-target-highlight" : ""}`} aria-labelledby={`heading-${category}`} data-assistant-target={`${category}-section`}>
      <header>
        <Icon size={31} weight="duotone" aria-hidden="true" />
        <div><h3 id={`heading-${category}`}>{CATEGORY_LABELS[category]}</h3><p>{totalCount ?? entries.length} {(totalCount ?? entries.length) === 1 ? "endpoint" : "endpoints"}</p></div>
      </header>
      <div className="endpoint-table-header" aria-hidden="true"><span>Property</span><span>Output type</span><span>Predicted value</span><span>Details</span></div>
      <div className="endpoint-list" role="table" aria-label={`${CATEGORY_LABELS[category]} endpoints`}>
        {entries.length ? entries.map(([rawKey, value]) => <EndpointDetails key={rawKey} rawKey={rawKey} value={value} category={category} metadata={endpointRegistry[rawKey]} />) : <p className="category-empty">No endpoints returned in this category.</p>}
      </div>
    </section>
  );
}
