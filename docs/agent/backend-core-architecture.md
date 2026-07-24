# Backend Agent Core Architecture

## Scope

The backend core adds one non-streaming OpenAI Agents SDK Agent around existing deterministic ADME services. It does not add a frontend, streaming, multi-agent orchestration, MCP, hosted tools, shell, file, web, deployment, or batch mutation tools.

```text
FastAPI /agent routes
  -> AgentRuntime
     -> one OpenAI Agents SDK Agent
     -> strict allowlisted function tools
        -> AgentToolService
           -> neutral deterministic services
           -> existing compound/predictor/registry/batch services
     -> SQLite repository
        -> conversation history
        -> business state
        -> confirmations/actions
        -> bounded JSON resources
        -> local audit events
```

## Neutral Services

- `app/services/prediction.py`: owns validation, predictor invocation, formatter grouping/enrichment, raw output, model metadata, mode, warnings, and disclaimer. It contains no chat wording or LLM behavior.
- `app/services/input_quality.py`: deterministic RDKit facts for parse status, fragments, heavy atoms, molecular weight, formal charge, metals, unusual elements, mixtures, and configured size warnings. It is not a statistical applicability-domain score.
- `app/services/comparison.py`: compares 2-5 completed prediction payloads neutrally. It does not rank, select a winner, apply a composite score, or invent directionality.

The legacy `app.agent.predict_adme` now delegates to the neutral prediction service while preserving the existing `/predict` and `/chat` response contracts.

## Runtime Boundary

`app/agent_runtime/runtime.py` creates exactly one `Agent` per request with:

- `OpenAIResponsesModel` from explicit environment configuration.
- Eleven strict function tools and no other tool type.
- `parallel_tool_calls=False`, bounded output, `max_turns=8`, and service-side maximum tool-call enforcement.
- Hosted SDK tracing disabled and sensitive trace input disabled.
- Application-owned audit events stored locally with redacted summaries.

Input guardrails run before the provider. Tool authorization is enforced structurally through the allowlist, session ownership, business state, resource ownership, and confirmation engine. Output policy validation runs before persistence/response.

## Feature Flag

`AGENT_ENABLED=false` is the default. Disabled Agent routes return `AGENT_DISABLED`, while existing health, Single, Batch, About, `/predict`, and legacy `/chat` remain available. Provider settings are loaded only for an enabled `/agent/chat` request.

## Local-Only Access Boundary

A bare `session_id` is not authentication. This implementation is acceptable only for the current single-user service bound to `127.0.0.1`. Any shared/LAN deployment requires at least a separate session token or HttpOnly cookie and a new security review.
