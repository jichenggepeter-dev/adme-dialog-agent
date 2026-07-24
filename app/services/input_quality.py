from __future__ import annotations

from typing import Any


COMMON_ATOMIC_NUMBERS = {1, 5, 6, 7, 8, 9, 14, 15, 16, 17, 35, 53}
METAL_ATOMIC_NUMBERS = {
    3, 4, 11, 12, 13, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
    31, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 55, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72,
    73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83,
}
DEFAULT_HEAVY_ATOM_WARNING = 100
DEFAULT_MOLECULAR_WEIGHT_WARNING = 1000.0


class InputQualityError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def assess_input_quality(
    smiles: str,
    *,
    heavy_atom_warning: int = DEFAULT_HEAVY_ATOM_WARNING,
    molecular_weight_warning: float = DEFAULT_MOLECULAR_WEIGHT_WARNING,
) -> dict[str, Any]:
    """Return deterministic structure checks, not an applicability-domain score."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors
    except ImportError as exc:
        raise InputQualityError(
            "RDKIT_NOT_AVAILABLE", "RDKit is required for input quality assessment."
        ) from exc

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return {
            "parse_status": "invalid",
            "fragment_count": 0,
            "heavy_atom_count": 0,
            "molecular_weight": None,
            "total_formal_charge": None,
            "metal_presence": False,
            "metal_elements": [],
            "unusual_elements": [],
            "mixture_warning": False,
            "size_warning": False,
            "warnings": ["Invalid SMILES string."],
            "is_applicability_domain_score": False,
        }

    fragments = Chem.GetMolFrags(molecule)
    atoms = list(molecule.GetAtoms())
    heavy_atom_count = molecule.GetNumHeavyAtoms()
    molecular_weight = float(Descriptors.MolWt(molecule))
    metal_elements = sorted(
        {atom.GetSymbol() for atom in atoms if atom.GetAtomicNum() in METAL_ATOMIC_NUMBERS}
    )
    unusual_elements = sorted(
        {
            atom.GetSymbol()
            for atom in atoms
            if atom.GetAtomicNum() not in COMMON_ATOMIC_NUMBERS
        }
    )
    mixture_warning = len(fragments) > 1
    size_warning = (
        heavy_atom_count > heavy_atom_warning
        or molecular_weight > molecular_weight_warning
    )
    warnings: list[str] = []
    if mixture_warning:
        warnings.append(
            "Disconnected components detected; confirm the intended salt or mixture structure."
        )
    if metal_elements:
        warnings.append("Metal-containing input detected.")
    if unusual_elements:
        warnings.append("Elements outside the common small-molecule set were detected.")
    if size_warning:
        warnings.append("Input exceeds the configured molecular size warning threshold.")

    return {
        "parse_status": "valid",
        "fragment_count": len(fragments),
        "heavy_atom_count": heavy_atom_count,
        "molecular_weight": round(molecular_weight, 4),
        "total_formal_charge": sum(atom.GetFormalCharge() for atom in atoms),
        "metal_presence": bool(metal_elements),
        "metal_elements": metal_elements,
        "unusual_elements": unusual_elements,
        "mixture_warning": mixture_warning,
        "size_warning": size_warning,
        "warnings": warnings,
        "is_applicability_domain_score": False,
    }
