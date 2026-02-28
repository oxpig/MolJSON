# MolJSON

Minimal MolJSON schema + RDKit conversion helpers.

Static JSON schema file: `schemas/moljson.schema.json`

## API

```python
from moljson import GetSchema, MolToJSON, MolFromJSON, CheckRoundTrip
```

- `GetSchema() -> dict`
- `MolToJSON(mol, *, atom_id_style="element") -> dict`
- `MolFromJSON(moljson) -> rdkit.Chem.Mol`
- `CheckRoundTrip(mol, *, atom_id_style="element") -> (ok, in_smiles, out_smiles, moljson)`

## Quick Start

```python
from rdkit import Chem
from moljson import GetSchema, MolToJSON, MolFromJSON, CheckRoundTrip

# 1) Get JSON schema
schema = GetSchema()

# 2) RDKit -> MolJSON
mol = Chem.MolFromSmiles("c1c[nH]cc1")
moljson = MolToJSON(mol)  # default atom ids: C1, C2, N1, ...

# Optional atom id style: a1, a2, a3, ...
moljson_a = MolToJSON(mol, atom_id_style="a")

# 3) MolJSON -> RDKit
mol2 = MolFromJSON(moljson)
smiles2 = Chem.MolToSmiles(mol2, canonical=True)

# 4) Round trip check (RDKit -> MolJSON -> RDKit)
ok, in_smiles, out_smiles, rt_json = CheckRoundTrip(mol)
print(ok, in_smiles, out_smiles)
```

## Notes

- MolJSON keys are: `atoms`, `bonds`, optional `charges`, optional `aromatic_n_h`.
- Empty optional fields are omitted on export.
- Stereochemistry fields are currently unsupported and rejected on import.

## OpenAI API Example (Structured MolJSON Output)

```python
import json
from openai import OpenAI
from moljson import GetSchema

client = OpenAI()  # uses OPENAI_API_KEY from env
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
