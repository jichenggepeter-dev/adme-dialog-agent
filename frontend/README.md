# ADME Lens Frontend

This directory contains the local Next.js 16 App Router interface for the ADME
Dialog Agent. It is a typed client of the FastAPI API and does not load or run
the scientific model itself.

## Architecture

- `app/`: server-rendered page shell, metadata, global styles, loading, and
  error boundaries.
- `components/prediction-workspace.tsx`: the client-side request lifecycle.
- `components/`: accessible input, status, result ledger, raw output, and state
  presentation.
- `lib/api.ts`: backend calls, timeouts, and stable error normalization.
- `lib/types.ts`: exact frontend representation of backend contracts.
- `e2e/`: Playwright user-flow and visual-capture tests.

The frontend uses native controls rather than a component framework. This keeps
the bundle small and lets native form and disclosure semantics carry keyboard
behavior.

## Run locally

From the repository root, use `make dev`. To run only this service:

```bash
cp .env.example .env.local
npm install
npm run dev
```

The default API URL is `http://127.0.0.1:8000`. Change
`NEXT_PUBLIC_API_BASE_URL` in `.env.local` if the backend uses another address.

## Checks

```bash
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

Install the Playwright browser once if needed:

```bash
npx playwright install chromium
```
