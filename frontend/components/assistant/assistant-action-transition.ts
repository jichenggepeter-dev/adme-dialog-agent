export type ActionPhase = "idle" | "preparing_action" | "collapsing_for_action" | "executing_action" | "highlighting_target" | "action_completed" | "action_failed";
export const ACTION_TIMING = { contentFade: 260, collapse: 580, highlight: 1200, completed: 1000 } as const;
export function reducedMotion(): boolean { return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
export async function transitionDelay(kind: keyof typeof ACTION_TIMING): Promise<void> { if (reducedMotion()) return; await new Promise((resolve) => window.setTimeout(resolve, ACTION_TIMING[kind])); }
export function clearHighlight(setter: (value: string | null) => void): void { window.setTimeout(() => setter(null), reducedMotion() ? 450 : ACTION_TIMING.highlight); }
