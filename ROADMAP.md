# Roadmap

ADME Dialog Agent follows a trust-first roadmap. Versions advance when a
specific user and contributor outcome is met, not when a feature count is
reached.

## v0.1.0: Research Preview baseline

Goal: another person can safely understand, install, test, and contribute to
the project.

- [x] Define product positioning and non-goals.
- [x] Remove local secrets and runtime data from the publishable file set.
- [x] Add license, contribution, conduct, security, and third-party documents.
- [ ] Curate current documentation and archive historical implementation notes.
- [ ] Add GitHub Actions for mock backend and frontend checks.
- [ ] Verify setup from a clean clone on a second environment.
- [ ] Complete a pre-publication secret and asset-rights review.
- [ ] Publish the initial baseline with an honest release date.

## v0.2.0: Trust and control

Goal: users can exercise, evaluate, export, and delete Agent state without
giving up control.

- Deterministic mock Agent provider for no-key development.
- Conversation and session export.
- Conversation and session deletion.
- Reproducible Agent evaluation dataset and runner.
- Confirmation, scientific-language, and provider-failure evaluations.
- Automated accessibility checks.
- Privacy and safety regression coverage.

## v0.3.0: Contributor experience

Goal: contributors can reproduce and extend the system efficiently.

- Containerized or equivalent reproducible development environment.
- Improved onboarding and example workflows.
- Public API documentation and migration guidance.
- Database schema migration tooling.
- One-command contributor verification.
- First structured external usability study.

## v1.0: Stable research tool

The project will consider `1.0` only after:

- API and storage compatibility policies are documented;
- clean-clone and CI checks are consistently reliable;
- Agent evaluations and safety regressions are public;
- privacy controls and data migrations are complete;
- critical scientific metadata has documented provenance;
- external users have validated the core workflow;
- dependency, model, dataset, and media licensing has been reviewed;
- maintenance and vulnerability-response expectations are sustainable.

## Not currently planned

- automatic candidate ranking or drug recommendation;
- clinical, medical, regulatory, or safety decision support;
- a general scientific-Agent framework or plugin marketplace;
- a hosted multi-user SaaS product;
- default telemetry or cloud synchronization.
