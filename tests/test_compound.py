from app.tools import compound


ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_resolve_direct_smiles_uses_rdkit():
    result = compound.resolve_compound(ASPIRIN)
    assert result["canonical_smiles"]
    assert result["molecular_formula"] == "C9H8O4"
    assert "<svg" in result["depiction_svg"]
    assert result["data_source"] == "Local RDKit"


def test_resolve_name_uses_pubchem_record(monkeypatch):
    monkeypatch.setattr(
        compound,
        "_fetch_pubchem",
        lambda namespace, identifier: {
            "PropertyTable": {
                "Properties": [
                    {
                        "CID": 2244,
                        "Title": "Aspirin",
                        "MolecularFormula": "C9H8O4",
                        "MolecularWeight": "180.16",
                        "SMILES": ASPIRIN,
                        "ConnectivitySMILES": ASPIRIN,
                    }
                ]
            }
        },
    )
    result = compound.resolve_compound("Aspirin")
    assert result["preferred_name"] == "Aspirin"
    assert result["pubchem_cid"] == 2244
    assert result["data_source"] == "PubChem + RDKit"
