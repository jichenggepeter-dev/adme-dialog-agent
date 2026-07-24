from __future__ import annotations

import re
import string


SMILES_SIGNAL_PATTERN = re.compile(r"(Cl|Br|[CNOSPFIbcnosp]|\=|\#|\(|\)|\[|\]|\d)")
TRAILING_PUNCTUATION = string.whitespace + ",.;:\"'`"


def _try_import_rdkit():
    try:
        from rdkit import Chem  # type: ignore
    except ImportError:
        return None
    return Chem


def validate_smiles(smiles: str) -> dict:
    input_smiles = smiles
    smiles = smiles.strip() if smiles else ""

    if not smiles:
        return {
            "is_valid": False,
            "input_smiles": input_smiles,
            "canonical_smiles": None,
            "error": "SMILES string is empty.",
        }

    Chem = _try_import_rdkit()
    if Chem is not None:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {
                "is_valid": False,
                "input_smiles": input_smiles,
                "canonical_smiles": None,
                "error": "Invalid SMILES string.",
            }

        canonical = Chem.MolToSmiles(mol, canonical=True)
        return {
            "is_valid": True,
            "input_smiles": input_smiles,
            "canonical_smiles": canonical,
            "error": None,
        }

    if any(character.isspace() for character in smiles):
        return {
            "is_valid": False,
            "input_smiles": input_smiles,
            "canonical_smiles": None,
            "error": "SMILES string contains whitespace; install RDKit for robust validation.",
        }

    if not SMILES_SIGNAL_PATTERN.search(smiles):
        return {
            "is_valid": False,
            "input_smiles": input_smiles,
            "canonical_smiles": None,
            "error": "SMILES string does not contain recognizable molecular tokens.",
        }

    return {
        "is_valid": True,
        "input_smiles": input_smiles,
        "canonical_smiles": None,
        "error": None,
    }


def extract_candidate_smiles(message: str) -> str | None:
    if not message or not message.strip():
        return None

    candidates: list[str] = []
    for token in message.split():
        cleaned = token.strip(TRAILING_PUNCTUATION)
        cleaned = cleaned.rstrip(".,;:")
        if not cleaned:
            continue
        if SMILES_SIGNAL_PATTERN.search(cleaned) and _looks_like_smiles_candidate(cleaned):
            candidates.append(cleaned)

    if not candidates:
        return None

    return max(candidates, key=len)


def _looks_like_smiles_candidate(token: str) -> bool:
    if token.isalpha() and token.upper() != token and len(token) > 2:
        return False

    if len(token) == 1 and token.upper() not in {"C", "N", "O", "S", "P", "F", "I"}:
        return False

    has_structural_marker = any(marker in token for marker in ("=", "#", "(", ")", "[", "]"))
    has_digit = any(character.isdigit() for character in token)
    has_common_atom = bool(re.search(r"Cl|Br|[CNOSPFIcnosp]", token))

    return has_common_atom and (has_structural_marker or has_digit or len(token) <= 8)
