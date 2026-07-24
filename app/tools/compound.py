from __future__ import annotations

import json
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.tools.smiles import validate_smiles


PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"


class CompoundResolutionError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def resolve_compound(query: str) -> dict:
    normalized = query.strip()
    if not normalized:
        raise CompoundResolutionError("INVALID_REQUEST", "Enter a compound name, PubChem CID, or SMILES string.")

    validation = validate_smiles(normalized)
    if validation["is_valid"]:
        canonical = validation["canonical_smiles"] or normalized
        return _local_compound(canonical, input_query=normalized)

    namespace = "cid" if normalized.lower().startswith("cid ") or normalized.isdigit() else "name"
    identifier = normalized[4:].strip() if normalized.lower().startswith("cid ") else normalized
    if namespace == "cid" and not identifier.isdigit():
        raise CompoundResolutionError("INVALID_REQUEST", "PubChem CID must be numeric.")

    payload = _fetch_pubchem(namespace, identifier)
    properties = payload.get("PropertyTable", {}).get("Properties", [])
    if not properties:
        raise CompoundResolutionError("COMPOUND_NOT_FOUND", "No matching compound was found.", 404)

    record = properties[0]
    canonical = record.get("ConnectivitySMILES") or record.get("SMILES")
    if not canonical:
        raise CompoundResolutionError("COMPOUND_NOT_FOUND", "The compound record did not include a usable SMILES string.", 404)

    compound = _local_compound(canonical, input_query=normalized)
    compound.update(
        {
            "preferred_name": record.get("Title") or f"PubChem CID {record.get('CID')}",
            "pubchem_cid": record.get("CID"),
            "molecular_formula": record.get("MolecularFormula") or compound["molecular_formula"],
            "molecular_weight": _float_or_none(record.get("MolecularWeight")) or compound["molecular_weight"],
            "isomeric_smiles": record.get("SMILES") or canonical,
            "data_source": "PubChem + RDKit",
        }
    )
    return compound


@lru_cache(maxsize=64)
def _fetch_pubchem(namespace: str, identifier: str) -> dict:
    properties = "Title,MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES"
    url = f"{PUBCHEM_BASE_URL}/{namespace}/{quote(identifier, safe='')}/property/{properties}/JSON"
    request = Request(url, headers={"User-Agent": "adme-dialog-agent/0.1"})
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise CompoundResolutionError("COMPOUND_NOT_FOUND", "No matching compound was found.", 404) from exc
        raise CompoundResolutionError("PUBCHEM_UNAVAILABLE", "PubChem could not complete the compound lookup.", 503) from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CompoundResolutionError("PUBCHEM_UNAVAILABLE", "PubChem could not be reached for compound metadata.", 503) from exc


def _local_compound(canonical_smiles: str, input_query: str) -> dict:
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        from rdkit.Chem.Draw import rdMolDraw2D
    except ImportError as exc:
        raise CompoundResolutionError(
            "MODEL_NOT_AVAILABLE",
            "RDKit is required for compound confirmation and structure depiction.",
            503,
        ) from exc

    molecule = Chem.MolFromSmiles(canonical_smiles)
    if molecule is None:
        raise CompoundResolutionError("INVALID_SMILES", "The backend could not parse this SMILES string.")

    canonical = Chem.MolToSmiles(molecule, canonical=True)
    isomeric = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    drawer = rdMolDraw2D.MolDraw2DSVG(520, 300)
    drawer.drawOptions().clearBackground = False
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, molecule)
    drawer.FinishDrawing()

    return {
        "input_query": input_query,
        "preferred_name": "Resolved SMILES compound",
        "pubchem_cid": None,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(molecule),
        "molecular_weight": round(float(Descriptors.MolWt(molecule)), 4),
        "canonical_smiles": canonical,
        "isomeric_smiles": isomeric,
        "data_source": "Local RDKit",
        "depiction_svg": drawer.GetDrawingText(),
        "warnings": [],
    }


def _float_or_none(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
