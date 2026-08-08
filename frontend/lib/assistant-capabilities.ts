import type { UIAction } from "./agent-types";

export type CapabilityResult = { targetId?: string; message: string };
export type RouteCapability = { execute(action: UIAction): Promise<CapabilityResult> | CapabilityResult };
const capabilities = new Map<string, RouteCapability>();

export function registerAssistantCapabilities(route: string, capability: RouteCapability): () => void {
  capabilities.set(route, capability);
  return () => { if (capabilities.get(route) === capability) capabilities.delete(route); };
}

export function getAssistantCapability(route: string): RouteCapability | undefined { return capabilities.get(route); }
export async function waitForAssistantCapability(route: string, timeoutMs = 10_000): Promise<RouteCapability | null> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const capability = capabilities.get(route); if (capability) return capability;
    await new Promise((resolve) => window.setTimeout(resolve, 25));
  }
  return null;
}
