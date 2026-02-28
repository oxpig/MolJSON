"""
MolJSON schema definition.

Public API:
- GetSchema() -> dict
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from rdkit import Chem

_PERIODIC_TABLE = Chem.GetPeriodicTable()
_DUMMY_SYMBOL = "*"


def _build_schema() -> Dict[str, Any]:
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
            "formal_charge": {"type": "integer", "minimum": -5, "maximum": 5},
        },
        "required": ["atom_id", "formal_charge"],
    }

    aromatic_n_h_items = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "atom_id": {"type": "string"},
            "hcount": {"type": "integer", "minimum": 1, "maximum": 2},
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
    return deepcopy(_build_schema())

