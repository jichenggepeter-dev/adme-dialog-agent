# Endpoint Metadata Provenance

The registry is built from primary materials installed with ADMET-AI 2.0.1:

- `resources/data/admet.csv`: raw task IDs, names, categories, task types,
  package-reported units, species, and official task/RDKit references.
- `physchem.py`: RDKit functions for molecular weight, LogP, HBA/HBD counts,
  stereo-center count, TPSA, QED, Lipinski rules satisfied, and alert counts.
- `drugbank.py`, `utils.py`, and `admet_model.py`: approved-DrugBank reference
  columns, exact percentile suffix, and percentile computation.
- Bundled ADMET-AI Web templates: classification values are documented as model
  probabilities that a molecule has the named property.

Registry responses expose source name, public reference where supplied, and
ADMET-AI package version, never local installation paths.

Metadata is not molecule-specific. No aspirin values or other prediction values
are stored in the registry. Model endpoints remain `partial` because package
metadata does not replace endpoint-specific review of the linked TDC or original
dataset definition. Model version is not reported by the installed public API.

