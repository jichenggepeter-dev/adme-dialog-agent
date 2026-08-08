# API change, deprecation, and migration policy

This policy applies to public FastAPI routes, request and response fields,
stable errors, confirmation flows, Agent stream events, evidence/source-card
data, and exported session documents.

## Version meanings

The REST contract uses `major.minor` versions. Application releases and API
contracts are independent: a release may improve the UI without changing the
API, while an API change must update this contract even if the product remains
a research preview.

- A **minor** contract change is backward compatible: for example, a new
  optional response field, optional request field with a default, route, or
  error code.
- A **major** contract change may break a correct existing client: for example,
  removing or renaming a route or field, making an optional field required,
  changing a field type or meaning, or changing confirmation semantics.
- A documentation correction that does not change executable behavior keeps
  the current contract version.

Stream events, evidence answers, and export documents also carry or document
their own format versions because they may evolve independently.

## Adding a compatible change

The pull request must update the v1 documentation and examples, update the
contract manifest when a route changes, and pass the contract tests. Clients
must tolerate documented new optional response fields and new error codes.
The change is recorded in release notes when it affects consumers.

## Deprecating a contract

A deprecation must be visible before removal. The pull request must:

1. mark the route or schema field deprecated in OpenAPI and the versioned docs;
2. name the supported replacement and the first deprecated contract version;
3. state the earliest removal version in release notes;
4. keep contract tests for both old and replacement behavior during the
   transition.

When practical, a deprecated contract remains available through at least the
next minor contract. A security, privacy, or scientific-safety problem may
require faster removal; that exception must be explained in the migration
guide. There are no deprecated v1 routes at publication time.

## Making a breaking change

Breaking changes require a new major directory such as `docs/api/v2/`; they do
not silently rewrite v1. The same pull request must add a migration document
under [migrations](migrations/README.md) containing:

- the old and new versions and the reason for the change;
- every affected route, field, error, event, or confirmation step;
- before-and-after request and response examples;
- ordered client update steps;
- rollout, compatibility-window, and rollback notes;
- the automated checks that prove both migration instructions and new
  examples match executable contracts.

If the backend temporarily serves both versions, the guide must say how a
client selects a version. If it does not, the guide must state the exact
cutover boundary. No migration may claim zero downtime or production
validation unless that was actually tested.
