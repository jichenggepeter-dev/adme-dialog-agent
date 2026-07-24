# Frontend Product Specification

## Product intent

The frontend is a single-molecule ADME/ADMET exploration workspace for
medicinal chemists, computational chemists, DMPK scientists, project teams, and
students. Its job is to turn one submitted SMILES string into a legible,
traceable view of computational predictions without implying experimental or
clinical certainty.

Design read: a scientific research application with calm, precise, instrument-
like language. It should feel closer to a well-maintained laboratory analysis
tool than a chatbot or marketing dashboard.

## Primary flow

```text
Open application
  -> check backend and prediction mode
  -> enter SMILES or select a verified example
  -> submit for backend validation
  -> wait through prediction/model initialization
  -> inspect canonical SMILES and computational summary
  -> scan grouped ADME/ADMET endpoints
  -> optionally inspect or copy raw JSON
  -> correct the input or run another prediction
```

The direct SMILES form is primary. Natural-language input is an optional second
mode that reuses the same result presentation and does not pretend to be a
general multi-turn AI assistant.

## MVP scope

Included:

- One single-molecule prediction workspace
- Direct SMILES and natural-language input modes
- Backend, mock/real, and model availability status
- Aspirin, caffeine, acetaminophen, and ibuprofen examples
- Validation, loading, success, empty, timeout, and error states
- Six grouped result sections
- Computational summary and canonical SMILES
- Exact raw response disclosure with copy action
- Persistent scientific disclaimer
- Responsive mobile, tablet, and desktop layouts

Excluded:

- Authentication, users, databases, saved projects, billing, or team spaces
- Deployment or cloud infrastructure
- Compound comparison and CSV batch upload
- Experimental result tracking
- Molecule-name lookup or drawing
- LLM-generated scientific conclusions
- Automatic scientific risk labels or invented endpoint thresholds

## Information architecture

```text
Header: product identity | backend and model status
Main:
  Context: concise purpose and mode warning
  Input workspace:
    Direct SMILES | Natural-language input
    Examples
    Field, validation/error, prediction action
  Result workspace:
    Identity strip: submitted and canonical SMILES
    Computational summary
    Category navigation and six result sections
    Raw JSON disclosure
  Empty/error/loading state when no result is available
Footer: scientific disclaimer and backend endpoint
```

The first viewport must expose the product identity, mode state, input, and
primary action. This is not a landing-page hero.

## Interaction rules

- Example selection populates the field but never submits automatically.
- Empty input cannot be submitted; backend validation remains authoritative.
- Submitted input remains in place after any error.
- Prediction requests use a generous timeout for first model initialization.
- Expensive requests are never retried automatically.
- Status is fetched once on page load and can be refreshed manually.
- Mock output always carries a visible development warning adjacent to results.
- Raw JSON is collapsed by default and uses native disclosure semantics.
- Async state uses `aria-live`; field errors use `aria-invalid` and
  `aria-describedby`.

## Visual system

### Direction

The signature element is a narrow vertical category index paired with a
laboratory-report result ledger. This gives long scientific output a clear scan
path without turning every value into a decorative card.

Design dials:

- Variation: 4/10
- Motion: 1/10
- Density: 6/10

### Color

- `ink`: `#17211d` for primary text
- `paper`: `#f4f7f5` for page background
- `surface`: `#ffffff` for working surfaces
- `line`: `#ccd6d0` for structural rules
- `teal`: `#0f6b5b` for actions and focus
- `blue`: `#315c89` for informational status
- `amber`: `#9a5b08` for mock/warning state
- `red`: `#a23b3b` for errors

Color never carries scientific good/bad meaning. Labels, icons, and text always
explain application status.

### Typography

- UI and narrative: system sans stack for reliable local rendering
- SMILES, endpoint names, values, and JSON: system monospace stack
- Numeric values use tabular figures
- Scale: 12px utility, 14px secondary, 16px body, 20px section, 30px page title
- Letter spacing remains normal

### Spacing and shape

- Base spacing unit: 4px
- Main rhythm: 8, 12, 16, 24, 32, 48px
- Inputs and buttons: 6px radius
- Panels and result sections: 8px radius maximum
- Status chips may be pill-shaped because they are compact state labels
- Shadows are avoided; borders and surface contrast communicate hierarchy

### States

- Focus: 2px teal outline with 2px offset
- Loading: stable structural rows and plain status copy; no fake percentage
- Success: canonical identity and result count appear before properties
- Warning: amber border plus explicit text, never color alone
- Error: inline red-accent panel with a concrete next action
- Empty: short prompt and direct path back to the input
- Reduced motion: all nonessential transitions disabled

### Data formatting

- Numbers use `Intl.NumberFormat`, up to 4 meaningful decimal places
- `null` renders as `Not available`
- Booleans render as `True` or `False`
- Nested values render as compact JSON while preserving the raw response
- Endpoint names are made readable visually while the exact raw key remains
  available in monospace text/title context
- No value is assumed to be a probability solely because it falls in `[0, 1]`

## Architecture decisions from reviewed skills

- `app/page.tsx` remains a Server Component and composes one client workspace.
- API calls, timeout handling, and error normalization live in `lib/api.ts`.
- Shared result presentation is composed once for direct and natural-language
  modes; variants are explicit rather than controlled by many boolean props.
- No global state library is needed; one local reducer/state boundary owns the
  request lifecycle.
- No component framework is needed. Native controls cover forms and disclosure,
  keeping dependencies and bundle size small.
- Independent status and user prediction work do not form a request waterfall.
- Metadata is defined once with the Next.js Metadata API.
- CSS uses explicit transitions only where interaction feedback benefits; no
  JavaScript animation library is introduced.
