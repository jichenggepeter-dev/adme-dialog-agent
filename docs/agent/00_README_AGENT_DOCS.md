# Agent documentation

The repository already contains a bounded conversational Agent. It is optional,
disabled by default, and designed to assist with the existing Single, Batch,
and About workflows without becoming an autonomous scientific decision-maker.

## Current behavior

- The FastAPI backend owns sessions, confirmation records, allow-listed tools,
  redacted audit events, and provider calls.
- The Next.js frontend owns visible conversation state and executes only
  allow-listed UI actions.
- Prediction and other consequential actions require the documented user
  confirmation.
- Agent access does not change the product's scientific boundary: no ranking,
  candidate recommendation, or clinical, regulatory, or safety conclusion.
- Provider configuration comes from environment variables. The repository does
  not require or prescribe a fixed local model server.

See `.env.example` for the supported configuration keys. Never hard-code or
commit a provider key, token, cookie, or private endpoint configuration.

## Authoritative current references

1. [Backend core architecture](backend-core-architecture.md)
2. [Backend API](backend-api.md)
3. [Session and confirmation](session-and-confirmation.md)
4. [Tool reference](tool-reference.md)
5. [Frontend Assistant contract](frontend-assistant-contract.md)
6. [Safety and audit](safety-and-audit.md)

Current code and tests are the executable authority. The documents above
explain their contracts and safety boundaries.

## Historical design and implementation records

The numbered specifications `01_*` through `06_*` are the original design
package. The remaining files whose names include `plan`, `report`, `review`,
`handoff`, or `audit` are implementation evidence from a point in time. They
are preserved for traceability but may describe an older floating-assistant
layout, a specific local provider, or work that has since been completed.

Do not treat those records as setup instructions or current API contracts.
When they conflict with current code, tests, or the references above, follow
the current implementation and open an issue if the current reference also
needs correction.
