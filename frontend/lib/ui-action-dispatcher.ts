import { uiActionSchema } from "./agent-schemas";
import { waitForAssistantCapability } from "./assistant-capabilities";
import type { UIAction } from "./agent-types";

const executed = new Set<string>();
const COLLAPSE_ACTIONS = new Set(["SET_COMPOUND_INPUT", "OPEN_MODEL_ENDPOINT", "OPEN_BATCH_JOB", "NAVIGATE", "SHOW_RESOURCE"]);
export type UIActionExecutionResult = { ok: true; actionId: string; target?: string; message: string } | { ok: false; actionId: string; code: "ACTION_STALE" | "ACTION_NOT_ALLOWED" | "ACTION_ROUTE_UNAVAILABLE" | "ACTION_TARGET_NOT_FOUND" | "ACTION_DUPLICATE" | "ACTION_INVALID"; message: string };

export function shouldCollapseForAction(action: UIAction): boolean { return COLLAPSE_ACTIONS.has(action.type); }
export async function executeUIAction(raw: unknown, options: { sessionId: string; stateVersion: number; currentRoute: string; navigate: (route: string) => void }): Promise<UIActionExecutionResult> {
  const parsed = uiActionSchema.safeParse(raw);
  if (!parsed.success) return failure("unknown", "ACTION_INVALID", "The Assistant action was malformed.");
  const action = parsed.data as UIAction;
  if (action.session_id !== options.sessionId) return failure(action.action_id, "ACTION_NOT_ALLOWED", "The action belongs to another session.");
  if (action.expected_state_version !== options.stateVersion) return failure(action.action_id, "ACTION_STALE", "Could not apply this action because the page state changed.");
  if (executed.has(action.action_id)) return failure(action.action_id, "ACTION_DUPLICATE", "This action was already applied.");
  const proposedRoute = action.target_route ?? options.currentRoute;
  const route = options.currentRoute.startsWith(`${proposedRoute}/`) ? options.currentRoute : proposedRoute;
  if (!route.startsWith("/single") && !route.startsWith("/batch") && !route.startsWith("/about")) return failure(action.action_id, "ACTION_NOT_ALLOWED", "The target route is not allowed.");
  if (route !== options.currentRoute && action.type !== "NAVIGATE") options.navigate(route);
  if (action.type === "NAVIGATE") { options.navigate(route); executed.add(action.action_id); return { ok: true, actionId: action.action_id, target: route, message: "Page opened" }; }
  const capability = await waitForAssistantCapability(route);
  if (!capability) return failure(action.action_id, "ACTION_ROUTE_UNAVAILABLE", "The target page is not ready for this action.");
  try {
    const result = await capability.execute(action); executed.add(action.action_id);
    return { ok: true, actionId: action.action_id, target: result.targetId, message: result.message };
  } catch {
    return failure(action.action_id, "ACTION_TARGET_NOT_FOUND", "The requested page target is not available.");
  }
}
type ActionFailureCode = "ACTION_STALE" | "ACTION_NOT_ALLOWED" | "ACTION_ROUTE_UNAVAILABLE" | "ACTION_TARGET_NOT_FOUND" | "ACTION_DUPLICATE" | "ACTION_INVALID";
function failure(actionId: string, code: ActionFailureCode, message: string): UIActionExecutionResult { return { ok: false, actionId, code, message }; }
export function resetExecutedActionsForTests() { executed.clear(); }
