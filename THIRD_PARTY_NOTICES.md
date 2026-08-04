# Third-Party Notices

ADME Dialog Agent source code is distributed under the MIT License. Third-party
software, model artifacts, datasets, services, and media keep their own terms.
The dependency lockfiles are the authoritative full package inventories; this
file highlights direct dependencies and scientifically important transitive
components reviewed on 2026-08-02.

## Python runtime

| Component | Reviewed version | Declared license | Use |
| --- | --- | --- | --- |
| FastAPI | 0.141.1 | MIT | HTTP API |
| Uvicorn | 0.52.1 | BSD-3-Clause | Local ASGI server |
| Pydantic | 2.13.4 | MIT | Request and response schemas |
| python-dotenv | 1.2.2 | BSD-3-Clause | Local environment loading |
| python-multipart | 0.0.32 | Apache-2.0 | Upload parsing |
| HTTPX | 0.28.1 | BSD-3-Clause | HTTP client and API tests |
| ADMET-AI | 2.0.1 | MIT | Local ADME/ADMET prediction package |
| pandas | 3.0.5 | BSD-3-Clause | Tabular prediction data |
| NumPy | 2.5.1 | Compound permissive expression in package metadata | Numeric data |
| OpenAI Python | 2.45.0 | Apache-2.0 | Optional provider client |
| OpenAI Agents SDK | 0.18.2 | MIT | Optional Agent orchestration |

RDKit 2026.3.4 (BSD-3-Clause) is both an optional project dependency and part
of the ADMET-AI stack. ADMET-AI also installs scientific transitive packages
including Chemprop, PyTorch, Lightning, SciPy, and scikit-learn; review
`uv.lock` and the installed package license files when redistributing a binary
environment rather than this source repository.

Development packages reviewed include pytest 9.1.1 (MIT) and httpx2 2.9.1
(BSD-3-Clause).

## Frontend runtime

| Component | Reviewed version | Declared license |
| --- | --- | --- |
| Phosphor Icons React | 2.1.10 | MIT |
| Next.js | 16.2.12 | MIT |
| React / React DOM | 19.2.4 | MIT |
| react-markdown | 10.1.0 | MIT |
| remark-gfm | 4.0.1 | MIT |
| Zod | 4.4.3 | MIT |

The direct frontend development packages are MIT-licensed except Playwright
1.61.1 and TypeScript 5.9.3, which declare Apache-2.0. Exact resolved versions
and all transitive packages are recorded in `frontend/package-lock.json`.

## ADMET-AI models and reference data

- Project: <https://github.com/swansonk14/admet_ai>
- Package license: MIT
- Citation: Kyle Swanson et al., “ADMET-AI: A machine learning ADMET platform
  for evaluation of large-scale chemical libraries,”
  <https://doi.org/10.1101/2023.12.28.573531>

The ADMET-AI 2.0.1 Python distribution installs Chemprop model checkpoints and
a DrugBank-derived approved-drug reference CSV inside the dependency package.
Those files are **not copied into this repository** and the repository MIT
license does not relicense them.

ADMET-AI states that its models were trained on Therapeutics Data Commons
(TDC) datasets. TDC licenses its code under MIT but instructs users to check
each dataset's own license. DrugBank states that use or redistribution of its
content requires an applicable license and citation. Users, especially
commercial users or anyone redistributing a built environment, must review
those upstream terms before enabling real mode or using DrugBank-derived
percentiles:

- <https://github.com/mims-harvard/TDC>
- <https://tdcommons.ai/single_pred_tasks/adme/>
- <https://go.drugbank.com/academic_research>

Mock Mode does not import or load ADMET-AI. It is the default documented path
for development, testing, and course demonstration.

## External services

Compound name and CID resolution may send the submitted identifier to PubChem.
PubChem is an external service, not bundled software. Direct SMILES resolution
and Mock Mode can run without PubChem. Review the service's current policies
before submitting confidential information.

## Project media and example data

The retained PNG files under `docs/images/` are maintainer-created captures of
this project's own interface using project demonstration content. Their hashes
and provenance are recorded in
[`docs/release/asset-provenance.md`](docs/release/asset-provenance.md).
Batch example files contain synthetic demonstration molecules and are project
content. An unused design image with insufficient source evidence was removed
during the 2026-08-02 review.

Do not add model weights, datasets, papers, screenshots, icons, or user files
without recording source, license, attribution requirements, and redistribution
permission. An accessible web page is not automatically reusable content.

## FDA evidence excerpts

The local evidence index contains short excerpts from seven FDA-authored web
pages captured on 2026-08-03. FDA states that, unless otherwise noted, FDA
website content is public domain. The excerpts retain canonical links, capture
dates, versions, lifecycle status, and stable source identifiers. One withdrawn
2020 guidance record is included only to test stale-source handling and is never
presented as current evidence.

- Corpus and exact source list: `resources/evidence/corpus.json`
- Workflow and update policy: `docs/evidence-rag.md`
- FDA website policy: <https://www.fda.gov/about-fda/about-website/website-policies>
- FDA withdrawn guidance list: <https://www.fda.gov/drugs/guidances-drugs/withdrawn-and-expired-guidances-drugs>

These excerpts do not relicense FDA-linked third-party content. Maintainers must
repeat the rights and lifecycle review before adding or replacing a source.
