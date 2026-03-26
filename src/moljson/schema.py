"""
MolJSON schema definition.

Public API:
- GetSchema() -> dict
- GetPaperSchema() -> dict
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from rdkit import Chem

_PERIODIC_TABLE = Chem.GetPeriodicTable()
_DUMMY_SYMBOL = "*"


def _build_charge_schema(*, use_enum: bool) -> Dict[str, Any]:
    if use_enum:
        return {"type": "integer", "enum": list(range(-5, 6))}
    return {"type": "integer", "minimum": -5, "maximum": 5}


def _build_hcount_schema(*, mode: str) -> Dict[str, Any]:
    if mode == "default":
        return {"type": "integer", "enum": [1]}
    if mode == "paper":
        return {"type": "integer", "minimum": 1, "maximum": 2}
    raise ValueError(f"Unsupported hcount schema mode: {mode}")


def _build_schema(*, charge_use_enum: bool, hcount_mode: str) -> Dict[str, Any]:
    element_enum = [_DUMMY_SYMBOL] + [
        _PERIODIC_TABLE.GetElementSymbol(i) for i in range(1, 119)
    ]

    element_schema: Dict[str, Any] = {
        "type": "string",
        "enum": element_enum,
        "description": "Element symbol like 'C' or 'Cl', or '*' dummy atom.",
    }

    atom_item: Dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "id": {"type": "string", "description": "Unique atom id."},
            "element": element_schema,
        },
        "required": ["id", "element"],
    }

    bond_order_schema: Dict[str, Any] = {
        "type": "number",
        "enum": [0, 1, 1.5, 2, 3],
        "description": "Bond order. Aromatic bonds are 1.5. ZERO bonds are 0.",
    }

    charges_items = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "atom_id": {"type": "string"},
            "formal_charge": _build_charge_schema(use_enum=charge_use_enum),
        },
        "required": ["atom_id", "formal_charge"],
    }

    aromatic_n_h_items = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "atom_id": {"type": "string"},
            "hcount": _build_hcount_schema(mode=hcount_mode),
        },
        "required": ["atom_id", "hcount"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["atoms", "bonds", "charges", "aromatic_n_h"],
        "properties": {
            "atoms": {"type": "array", "items": atom_item},
            "bonds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "order": bond_order_schema,
                    },
                    "required": ["source", "target", "order"],
                },
            },
            "charges": {
                "type": ["array", "null"],
                "description": "Sparse list of NON-ZERO formal charges. Null means none.",
                "items": charges_items,
            },
            "aromatic_n_h": {
                "type": ["array", "null"],
                "description": (
                    "Sparse list of aromatic nitrogens with explicit hydrogen count. "
                    "Null means none."
                ),
                "items": aromatic_n_h_items,
            },
        },
    }


def GetSchema() -> Dict[str, Any]:
    """Return a deep copy of the MolJSON schema."""
    return deepcopy(_build_schema(charge_use_enum=True, hcount_mode="default"))


def GetPaperSchema() -> Dict[str, Any]:
    """Return the original paper/OpenAI MolJSON schema with min/max ranges."""
    return deepcopy(_build_schema(charge_use_enum=False, hcount_mode="paper"))
