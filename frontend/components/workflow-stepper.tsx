import { Check } from "@phosphor-icons/react";

const STEPS = ["Upload", "Map Columns", "Validate", "Run & Review"];

export function WorkflowStepper({ current }: { current: number }) {
  return <ol className="workflow-stepper" aria-label="Batch workflow progress">
    {STEPS.map((label, index) => <li key={label} className={index + 1 < current ? "complete" : index + 1 === current ? "current" : "pending"} aria-current={index + 1 === current ? "step" : undefined}>
      <span>{index + 1 < current ? <Check size={18} weight="bold" aria-hidden="true" /> : String(index + 1).padStart(2, "0")}</span>
      <div><b>{label}</b><small>{index + 1 < current ? "Complete" : index + 1 === current ? "Current step" : "Not started"}</small></div>
    </li>)}
  </ol>;
}
