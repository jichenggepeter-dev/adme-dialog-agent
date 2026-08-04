# PR Review App

The PR Review App is a temporary website for reviewing a proposed change before
it is merged. It is not a production deployment and it does not need an LLM API
key.

For a professor or product reviewer, the important idea is simple:

1. a pull request contains a proposed change;
2. Render builds that exact source revision;
3. GitHub shows a **View deployment** link;
4. the reviewer can use the real frontend and API with fixed Mock Agent
   behavior;
5. Render removes the temporary environment when the pull request is closed or
   merged.

This is a common engineering-to-product handoff pattern. Automated tests answer
“did the contracts still pass?” while the Review App answers “can a person see
and understand the change?”

## What each environment is for

| Environment | Main question | Data and model behavior |
| --- | --- | --- |
| Local development | Can the contributor build the change? | Local files and deterministic fixtures |
| Continuous integration (CI) | Did tests, lint, types, and builds pass? | Automated and isolated |
| PR Review App | Can a reviewer experience this exact change? | Temporary state and Mock Agent v1 |
| Production | Can real users rely on an operated service? | Not provided by this project |

The Review App must never be presented as production, staging, or scientific
validation.

## Review safety boundary

Every Review App page displays:

- `PR Preview · Mock Agent v1`;
- the source revision used to build the page;
- a reminder that state is temporary and synthetic;
- a reminder that the output is not a scientific conclusion.

The backend runs with `AGENT_PROVIDER_MODE=mock` and
`ADME_MOCK_MODE=true`. It does not accept or require OpenAI, ChatGPT, or other
model-provider credentials. Reviewers should use the fixed scenario picker in
the Assistant instead of expecting free-form model reasoning.

The five versioned scenarios are:

| Scenario | What the reviewer sees |
| --- | --- |
| Successful tool run | Model information returned through the normal tool contract |
| Structure confirmation | A fixed `CCO` structure that must be approved before Mock prediction |
| Provider timeout | A stable retryable timeout state |
| Tool failure | A stable missing-resource tool error |
| Insufficient evidence | A source card with no evidence and no unsupported claims |

The message field is still part of the real interface, but its text does not
select or alter the fixed scenario. This keeps product demonstrations
reproducible.

## Render setup

The repository contains a root `render.yaml` Blueprint with:

- one private FastAPI service;
- one public Next.js service;
- same-origin `/api` forwarding from Next.js to the private API;
- ephemeral files under `/tmp`;
- one process for the SQLite-backed API;
- manual, three-day PR Preview Environments.

Manual mode controls cost. To request a preview, add `[render preview]` to the
pull-request title. Render then posts deployment status on the PR. Click
**View deployment** next to the web service. Removing the phrase, closing the
PR, merging the PR, or reaching the expiry window removes the preview.

Account setup is intentionally not automated. A repository administrator must:

1. use a Render workspace on the Pro plan or higher;
2. connect the GitHub repository to Render;
3. create a Blueprint from the repository's `render.yaml`;
4. review the billed `starter` service choices before enabling previews.

Render bills preview resources while they run. No deployment should be enabled
without the maintainer accepting that external cost.

Official references:

- [Render Preview Environments](https://render.com/docs/preview-environments)
- [Render Blueprint YAML reference](https://render.com/docs/blueprint-spec)
- [Render Python version configuration](https://render.com/docs/python-version)

## Reviewer checklist

Before accepting a visible product change:

1. open the deployment from the intended pull request;
2. compare the banner revision with the source revision shown by GitHub;
3. confirm the backend and Mock Predictions status pills are visible;
4. exercise the scenario relevant to the change;
5. check desktop and narrow-screen layout when the UI changed;
6. do not enter private structures or real user data;
7. record what was observed in the PR, including any untested state.

## What this does not prove

A passing Review App does not prove:

- real ADMET-AI model availability or accuracy;
- a real LLM provider integration;
- PubChem availability;
- production security, authentication, scale, durability, or monitoring;
- clinical, regulatory, safety, efficacy, or candidate-selection conclusions.

The Review App is a product-review aid. Repository tests and scientific
validation remain separate responsibilities.
