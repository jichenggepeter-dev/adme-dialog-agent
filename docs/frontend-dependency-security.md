# Frontend dependency security

This note records the production-dependency review performed for Issue #2 on
August 1, 2026. It is a point-in-time assessment, not a guarantee that future
dependency versions are free of advisories.

## Upgrade decision

- `next` was upgraded from 16.2.10 to the current stable patch, 16.2.12.
- `eslint-config-next` was kept aligned at 16.2.12.
- `package-lock.json` was regenerated with npm.
- Preview, canary, major-version downgrade, and `npm audit fix --force` paths
  were rejected because they do not provide a compatible stable fix.

The upgrade removes the direct Next.js advisories reported against 16.2.10.
For example, the Next.js rewrite SSRF advisory affects 16.x versions before
16.2.11 and lists 16.2.11 as patched:

- [GHSA-p9j2-gv94-2wf4](https://github.com/vercel/next.js/security/advisories/GHSA-p9j2-gv94-2wf4)

## Remaining production audit findings

After the upgrade, `npm audit --omit=dev` reports three high-severity package
findings: `next`, `postcss`, and `sharp`. The `next` entry is an aggregate result
caused by its two transitive dependencies; it does not contain a remaining
direct Next.js advisory. The underlying advisories and application exposure are
reviewed below.

### PostCSS bundled by Next.js

Next.js 16.2.12 bundles PostCSS 8.4.31. npm reports these advisories:

- [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)
  (unescaped `</style>` during CSS stringification)
- [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q)
  (file read through an attacker-controlled `sourceMappingURL`)
- [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849)
  (path traversal while loading a previous source map)

These paths require attacker-controlled CSS to be passed through PostCSS. This
application only compiles repository-owned CSS during the build. It has no CSS
upload, theme editor, runtime CSS transformation, or third-party stylesheet
build service. The Batch upload accepts compound data and sends it to the
FastAPI backend; it is not processed as CSS. The vulnerable package is present,
but the documented application workflow does not expose the required input
path.

Current disposition: accepted as a low-exposure upstream risk for the local
research preview. Recheck when Next.js publishes a stable release that bundles
PostCSS 8.5.18 or newer. Do not override Next.js's private PostCSS copy without
upstream compatibility guidance.

### sharp bundled by Next.js

Next.js 16.2.12 installs sharp 0.34.5 as an optional dependency. npm reports:

- [GHSA-f88m-g3jw-g9cj](https://github.com/advisories/GHSA-f88m-g3jw-g9cj)
  (inherited libvips vulnerabilities when processing untrusted images)

The frontend does not import `next/image`, configure remote image sources, or
accept image uploads. Its only public download is a CSV template. Therefore the
current product does not send user-controlled images to sharp or the Next.js
image optimizer.

Current disposition: accepted as a low-exposure upstream risk for the local
research preview. Recheck when Next.js supports sharp 0.35.0 or newer. If an
image upload, remote-image feature, or `next/image` usage is added first, this
assessment must be reopened before that feature ships.

## Follow-up procedure

For each stable Next.js patch:

1. Update `next` and `eslint-config-next` together.
2. Regenerate the lockfile with npm.
3. Run `npm ci` and `npm audit --omit=dev`.
4. Run lint, type checking, unit tests, and a production build.
5. Update this note if the dependency tree or application exposure changes.

The audit currently suggests a forced downgrade to Next.js 9.3.3 for the
remaining transitive findings. That is not a valid remediation for this Next.js
16 application and must not be applied.
