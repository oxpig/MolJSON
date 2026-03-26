# MolJSON

This repo contains the MolJSON structured-output JSON schema and related scripts. The MolJSON schema was designed to enable Large Language Models to interpret and emit molecular structures with higher accuracy.

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

# 3) MolJSON -> RDKit
mol2 = MolFromJSON(moljson)

# 4) Round trip check
ok, in_smiles, out_smiles, rt_json = CheckRoundTrip(mol)
print(ok, in_smiles, out_smiles)
```

## Example Notebooks
A simple walkthrough of the MolJSON functions can be found in `examples/walkthrough.ipynb`. This shows:
- Loading and printing the schema
- RDKit -> MolJSON conversion
- MolJSON -> RDKit conversion
- Round-trip checks

For a minimal `OpenAI` API example see `examples/openai_moljson_example.ipynb`.

For a minimal `Anthropic` API example see `examples/anthropic_moljson_example.ipynb`.

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

## Format Notes
MolJSON uses the keys `atoms`, `bonds`, `charges`, and `aromatic_n_h`. The `charges` and `aromatic_n_h` keys are only required for correct charge and valence assignment. The `MolToJSON` function only outputs `charges` and `aromatic_n_h` when they are present in the molecule. If you want `MolToJSON` to be schema-strict, you can add the missing keys explicitly with ```moljson.setdefault("charges", None)``` and ```moljson.setdefault("aromatic_n_h", None)```

## Paper Schema
To ensure compatibility with both the OpenAI and Anthropic APIs, the MolJSON schema provided in this repo has been slightly modified. The original schema used in the paper can be found in `schemas/paper_moljson.schema.json`. The Anthropic API currently does not support minimum/maximum integer ranges, so the `charges` and `aromatic_n_h` keys now use an enumeration of integers. This is functionally equivalent and should not impact performance.

## Citation

```bibtex
@article{runcie2026MolJSON,
  title={},
  author={Nicholas T. Runcie and Charlotte M. Deane and Fergus Imrie},
  journal={},
  year={2026},
  doi={},
  url={},
}
```
