export const REVIEW_MODE = process.env.NEXT_PUBLIC_REVIEW_MODE === "true";
export const MOCK_AGENT_MODE =
  process.env.NEXT_PUBLIC_AGENT_PROVIDER_MODE === "mock";

export type MockScenarioId =
  | "success"
  | "confirmation"
  | "timeout"
  | "tool_failure"
  | "insufficient_evidence";

export type MockScenarioSelection = {
  catalog_version: 1;
  id: MockScenarioId;
};

export const MOCK_SCENARIOS: ReadonlyArray<{
  id: MockScenarioId;
  label: string;
  description: string;
}> = [
  {
    id: "success",
    label: "Successful tool run",
    description: "Shows a supported answer from the local FDA evidence corpus.",
  },
  {
    id: "confirmation",
    label: "Structure confirmation",
    description: "Resolves ethanol (CCO) and waits for approval before Mock prediction.",
  },
  {
    id: "timeout",
    label: "Provider timeout",
    description: "Shows the retryable timeout and recovery state.",
  },
  {
    id: "tool_failure",
    label: "Tool failure",
    description: "Shows a missing-resource tool error.",
  },
  {
    id: "insufficient_evidence",
    label: "Insufficient evidence",
    description: "Shows a no-evidence source card with no claims.",
  },
] as const;

export const DEFAULT_MOCK_SCENARIO: MockScenarioId = "success";

export function mockScenarioSelection(
  id: MockScenarioId,
): MockScenarioSelection {
  return { catalog_version: 1, id };
}

export function reviewRevision(): string {
  const value = process.env.NEXT_PUBLIC_REVIEW_REVISION?.trim();
  return value ? value.slice(0, 12) : "local";
}
