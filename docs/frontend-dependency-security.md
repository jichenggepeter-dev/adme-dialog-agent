# Frontend dependency security

This is a point-in-time dependency review for Issue #18, completed on
August 8, 2026. It does not guarantee that future advisory data will remain
unchanged.

## Current result

- `next` and `eslint-config-next` are pinned together at stable version 16.3.0.
- Next.js now resolves PostCSS 8.5.23 and optional sharp 0.35.3.
- The lockfile received only compatible, non-forced audit updates.
- `npm audit --omit=dev`: 0 vulnerabilities.
- `npm audit`: 0 vulnerabilities.

This replaces the August 1 assessment for Next.js 16.2.12. The earlier
PostCSS, sharp, and nanoid findings are no longer present in the installed
dependency tree. No preview/canary release, forced downgrade, or
`npm audit fix --force` was used.

## Response procedure

When a new advisory or high-risk dependency change appears:

1. Reproduce it from a clean `npm ci` install and separate production from
   development-only findings with `npm audit --omit=dev`.
2. Prefer the smallest compatible stable update; update `next` and
   `eslint-config-next` together and review the lockfile diff.
3. Do not use a forced fix, unsupported override, preview release, or major
   downgrade merely to make the audit command green.
4. Run lint, type checking, unit tests, production build, and relevant E2E.
5. If no compatible fix exists, document the affected path and exposure here.
   Block any new feature that would expose that path until the risk is fixed or
   explicitly reviewed through `SECURITY.md`.

This repository is a local research preview, not a production or clinical
service. That boundary reduces exposure but does not replace dependency review.
