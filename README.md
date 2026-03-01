# MolJSON

This repo contains the MolJSON structured-output JSON schema and related scripts. The MolJSON schema was designed to enable large language models to emit molecular structures with higher accuracy.

## What Is Included

- Public API:
  - `GetSchema() -> dict`
  - `MolToJSON(mol, *, atom_id_style="element") -> dict`
  - `MolFromJSON(moljson) -> rdkit.Chem.Mol`
  - `CheckRoundTrip(mol, *, atom_id_style="element") -> (ok, in_smiles, out_smiles, moljson)`
- Static schema file:
  - `schemas/moljson.schema.json`

## Installation

This repo is pip-installable via `pyproject.toml`.

```bash
git clone https://github.com/oxpig/MolJSON.git
# or: git clone git@github.com:oxpig/MolJSON.git
cd MolJSON
pip install -e .
```

## Quick Start

```python
from rdkit import Chem
from moljson import GetSchema, MolToJSON, MolFromJSON, CheckRoundTrip

# 1) Get MolJSON schema
schema = GetSchema()

# 2) RDKit -> MolJSON
mol = Chem.MolFromSmiles("c1c[nH]cc1")
moljson = MolToJSON(mol)  # default atom IDs: C1, C2, N1, ...
moljson_a = MolToJSON(mol, atom_id_style="a")  # a1, a2, a3, ...

# 3) MolJSON -> RDKit
mol2 = MolFromJSON(moljson)

# 4) Round trip check
ok, in_smiles, out_smiles, rt_json = CheckRoundTrip(mol)
print(ok, in_smiles, out_smiles)
```

## Format Notes

- MolJSON keys: `atoms`, `bonds`, optional `charges`, optional `aromatic_n_h`.
- `MolToJSON` only emits `charges` and `aromatic_n_h` when they are present in the molecule.

If you want `MolToJSON` output to be schema-strict, add missing keys explicitly:

```python
moljson.setdefault("charges", None)
moljson.setdefault("aromatic_n_h", None)
```

## OpenAI API Example

```python
import json
from openai import OpenAI
from moljson import GetSchema

client = OpenAI()  # uses OPENAI_API_KEY
schema = GetSchema()

response = client.responses.create(
    model="gpt-5-nano",
    reasoning={"effort": "low"},
    input="Convert the molecule from SMILES to MolJSON: CCO",
    text={
        "verbosity": "low",
        "format": {
            "type": "json_schema",
            "name": "MolJSON",
            "strict": True,
            "schema": schema,
        },
    },
    store=False,
)

moljson = json.loads(response.output_text)
print(moljson)
```

## Example Notebook

See `examples/example.ipynb` for a minimal runnable walkthrough of:
- loading and printing the schema
- RDKit -> MolJSON conversion
- MolJSON -> RDKit conversion
- round-trip checks
