# Issue #10 Activity and Evidence Trace Report

- Date: 2026-08-06
- Baseline: `16434d246c2f1d5e8e38912935ecb494e5b7b1c6`
- Branch: `agent/issue-10-activity-trace`
- Status: implementation verified and prepared for pull-request review

## Outcome

Issue #10 is implemented as one small vertical slice. The backend records the
actual UTC start and completion of each represented allowlisted tool operation
and measures duration with a monotonic clock. The stream emits a paired
`tool_started` and `tool_completed` view in recorded operation order. The
frontend derives a collapsed, per-message activity and evidence timeline from
strictly validated events.

This is not chain-of-thought display, provider tracing, or an audit-log
endpoint. The current runtime returns a buffered response, so lifecycle events
are serialized after the runtime finishes while retaining the operation times
captured at the service boundary. Converting the runtime to true live tool
streaming remains outside this issue.

## User-visible behavior

- A native disclosure shows response-stream, tool, evidence, confirmation,
  error, and response-completion activities in order.
- Each entry has visible status text and a machine-readable timestamp. Tool
  completions include elapsed milliseconds.
- Evidence activities link to the exact existing citation source when its URL
  is safe HTTP(S) without embedded credentials.
- No-evidence results remain explicitly unknown and suggest refining the
  question.
- Error recovery is a user-initiated **Return to message box** button. It only
  moves focus; it never submits, retries, confirms, or executes a tool.

## Privacy and isolation boundary

The projection constructs new objects from an exact allowlist. It does not
retain or spread the original event and does not copy user text, model output
text, raw errors, tool arguments, confirmation payloads, resource contents,
provider bodies, prompts, headers, credentials, or Batch data. The existing
stream consumer rejects mismatched session, message, correlation, sequence,
and terminal identities. Final placeholder replacement additionally requires
the same session and message identity.

The timeline is capped at 40 items per assistant message. No route, database
table, dependency, provider permission, tool permission, or persistence format
was added.

## Independent review

ChatGPT Pro reviewed the locked design as an independent critic in
[this conversation](https://chatgpt.com/c/6a74e522-7894-83ea-97a2-72566aa22dc2).
It returned **PASS WITH CHANGES**. The implementation adopted its useful
minimal corrections:

- renamed the heartbeat projection from “request accepted” to the truthful
  “response stream active” and deduplicated repeated heartbeats;
- added a keyboard-operable recovery control with no automatic side effect;
- added safe evidence-link filtering and an explicit new-tab accessible name;
- strengthened session-aware placeholder replacement and isolation tests;
- made each trace disclosure accessible name response-specific.

The suggested redesign into true real-time tool lifecycle emission was not
added because it would exceed the buffered runtime boundary and the agreed
single-issue scope. The report and UI state that limitation explicitly.

## Verification evidence

- Full backend suite: 143 passed, 2 skipped (the repository's opt-in external
  integration checks).
- Full frontend unit/component suite: 63 passed.
- Frontend TypeScript and ESLint: passed.
- Production build: passed with Next.js 16.2.12.
- Playwright activity/evidence flow: 2 passed (desktop and mobile), including
  keyboard disclosure and keyboard activation of the exact intercepted source
  destination.

- Documentation links: 80 Markdown files and 96 repository-local links checked,
  with 0 broken links.
