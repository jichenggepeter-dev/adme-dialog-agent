# Frontend QA

QA date: 2026-07-10

## Automated checks

```text
npm run lint       passed
npm run typecheck  passed
npm run test       9 tests passed
npm run build      passed (Next.js 16.2.10)
npm run test:e2e   12 tests passed across desktop and mobile
```

Playwright covered mock prediction success, raw JSON disclosure, invalid SMILES
with input retention, example selection, backend unavailability, keyboard
operation, and horizontal overflow. Desktop Chrome and Pixel 7 profiles passed.

## Accessibility review

- Page uses header, main, section, nav, footer, headings, labels, definition
  lists, buttons, and native details/summary semantics.
- A keyboard-visible skip link targets the prediction workspace.
- Input helper and error text are associated through `aria-describedby`.
- Invalid input sets `aria-invalid`; request state sets `aria-busy`.
- Backend status, mock mode, loading, and results use polite live regions or
  status semantics where appropriate.
- All controls are keyboard reachable and use visible `:focus-visible` rings.
- The disclosure opens with Enter and has an accessible text label.
- Warning and error states pair color with explicit text and border treatment.
- Touch controls have stable dimensions and no horizontal overflow at 390px.
- Reduced-motion preference disables smooth scrolling and transition duration.

No critical accessibility issue was found in the implemented MVP flows. A
future iteration should add an automated axe scan and test with VoiceOver.

## Product usability review

- The expected SMILES input and a valid example are visible in the first view.
- Mock mode is stated in the status row, before input, and beside returned data.
- Backend and model states are readable without opening developer tools.
- The direct prediction action is dominant; natural-language input is clearly a
  secondary, rule-based mode.
- Canonical identity and summary precede the longer endpoint ledger.
- Raw data stays available without competing with the main result hierarchy.
- The scientific disclaimer is persistent at the bottom of every state.

## Design review

The interface uses a restrained scientific report direction: off-white paper,
dark ink, teal actions, amber development warnings, rules rather than shadows,
and monospace treatment for molecular and endpoint data. The category index and
result ledger provide the distinctive organizing device. The layout avoids AI
gradients, glass effects, decorative chemistry imagery, and excessive cards or
motion.

Visual inspection was completed for the empty desktop state, result desktop
state, and result mobile state:

- `docs/images/frontend-empty-desktop.png`
- `docs/images/frontend-results-desktop.png`
- `docs/images/frontend-results-mobile.png`

The review reduced the display heading size, kept mobile action labels readable,
and changed the skip link to appear only for keyboard-visible focus.

## Engineering review

- The page shell is server-rendered; only the interactive workspace and raw-copy
  behavior are client components.
- API calls and errors are centralized in `lib/api.ts`.
- Backend URL and timeout are centralized constants.
- Direct and natural-language workflows share result presentation.
- No global state, animation package, or component framework was added.
- Status and prediction requests are independent; prediction is never retried
  automatically.
- TypeScript API types match the stabilized backend response models.

The first production build failed only because the execution sandbox blocked a
Turbopack worker port. The same build passed outside that sandbox. This is not a
project or local-machine limitation.
