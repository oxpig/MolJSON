"""
MolJSON <-> RDKit conversion.

Public API:
- MolToJSON(mol) -> dict
- MolFromJSON(moljson) -> rdkit.Chem.Mol
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from rdkit import Chem

_PERIODIC_TABLE = Chem.GetPeriodicTable()
_DUMMY_SYMBOL = "*"

_ALLOWED_BOND_ORDERS: List[float] = [0.0, 1.0, 1.5, 2.0, 3.0]

_ORDER_TO_BONDTYPE: Dict[float, Chem.BondType] = {
    0.0: Chem.BondType.ZERO,
    1.0: Chem.BondType.SINGLE,
    1.5: Chem.BondType.AROMATIC,
    2.0: Chem.BondType.DOUBLE,
    3.0: Chem.BondType.TRIPLE,
}

_BONDTYPE_TO_ORDER: Dict[Chem.BondType, float] = {
    Chem.BondType.ZERO: 0.0,
    Chem.BondType.SINGLE: 1.0,
    Chem.BondType.AROMATIC: 1.5,
    Chem.BondType.DOUBLE: 2.0,
    Chem.BondType.TRIPLE: 3.0,
}


def _require_list_optional(data: Dict[str, Any], key: str) -> List[Any]:
    if key not in data or data[key] is None:
        return []
    v = data[key]
    if not isinstance(v, list):
        raise ValueError(f"moljson['{key}'] must be a list when present")
    return v


def _is_valid_element_symbol(sym: Any) -> bool:
    if not isinstance(sym, str):
        return False
    s = sym.strip()
    if not s:
        return False
    if s == _DUMMY_SYMBOL:
        return True
    return int(_PERIODIC_TABLE.GetAtomicNumber(s)) > 0


def _make_rdkit_atom_from_symbol(sym: str) -> Chem.Atom:
    if sym == _DUMMY_SYMBOL:
        return Chem.Atom(0)
    return Chem.Atom(sym)


def _infer_and_mark_aromatic_atoms(mol: Chem.Mol) -> None:
    aromatic_atom_idxs: set[int] = set()
    for bond in mol.GetBonds():
        if bond.GetBondType() == Chem.BondType.AROMATIC:
            aromatic_atom_idxs.add(bond.GetBeginAtomIdx())
            aromatic_atom_idxs.add(bond.GetEndAtomIdx())
    for idx in aromatic_atom_idxs:
        mol.GetAtomWithIdx(idx).SetIsAromatic(True)


def _normalize_bond_order(order: Any) -> float:
    if not isinstance(order, (int, float)):
        raise ValueError(
            f"Bond order must be a number (0, 1, 1.5, 2, 3). Got: {type(order)}"
        )
    o = float(order)
    for allowed in _ALLOWED_BOND_ORDERS:
        if abs(o - allowed) < 1e-9:
            return allowed
    raise ValueError(f"Unsupported bond order: {order!r} (allowed: 0, 1, 1.5, 2, 3)")


def _apply_aromatic_n_h(
    mol: Chem.Mol,
    aromatic_n_h: List[Dict[str, Any]],
    id_to_idx: Dict[str, int],
) -> None:
    if not aromatic_n_h:
        return

    if not isinstance(aromatic_n_h, list):
        raise ValueError("aromatic_n_h must be a list when present")

    for entry in aromatic_n_h:
        if not isinstance(entry, dict):
            raise ValueError("aromatic_n_h entries must be objects")
        atom_id = entry.get("atom_id")
        hcount = entry.get("hcount")

        if atom_id is None or hcount is None:
            raise ValueError("aromatic_n_h entries require 'atom_id' and 'hcount'")
        if not isinstance(atom_id, str):
            raise ValueError("aromatic_n_h.atom_id must be a string")
        if atom_id not in id_to_idx:
            raise ValueError(f"aromatic_n_h references unknown atom_id: {atom_id}")
        if not isinstance(hcount, int):
            raise ValueError("aromatic_n_h.hcount must be an integer")
        if hcount != 1:
            raise ValueError("aromatic_n_h.hcount must be 1")

        idx = id_to_idx[atom_id]
        atom = mol.GetAtomWithIdx(idx)
        if atom.GetSymbol() != "N":
            raise ValueError(f"aromatic_n_h.atom_id={atom_id} is not a nitrogen atom")

        atom.SetIsAromatic(True)
        atom.SetNoImplicit(True)
        atom.SetNumExplicitHs(int(hcount))

    try:
        mol.UpdatePropertyCache(strict=False)
    except Exception:
        pass


def MolFromJSON(moljson: Dict[str, Any]) -> Chem.Mol:
    """
    Build an RDKit molecule from MolJSON.

    Supported features include aromatic bond handling, ZERO bonds, sparse formal
    charges, and sparse aromatic_n_h annotations. Stereochemistry fields are not
    supported and duplicate or conflicting edges are rejected.
    """
    for forbidden in ("alkene_stereo", "atom_stereo", "bond_stereo", "stereo"):
        if forbidden in moljson:
            raise ValueError(
                f"Stereochemistry is not supported in MolJSON: found forbidden field "
                f"'{forbidden}'"
            )

    atoms = _require_list_optional(moljson, "atoms")
    bonds = _require_list_optional(moljson, "bonds")
    charges = _require_list_optional(moljson, "charges")
    aromatic_n_h = _require_list_optional(moljson, "aromatic_n_h")

    rw = Chem.RWMol()
    id_to_idx: Dict[str, int] = {}

    for atom_obj in atoms:
        if not isinstance(atom_obj, dict):
            raise ValueError("Each atom must be an object")
        atom_id = atom_obj.get("id")
        element = atom_obj.get("element")

        if not isinstance(atom_id, str):
            raise ValueError(f"Atom id must be a string. Got: {type(atom_id)}")
        if atom_id in id_to_idx:
            raise ValueError(f"Duplicate atom id: {atom_id}")
        if not _is_valid_element_symbol(element):
            raise ValueError(f"Unsupported/invalid element symbol: {element!r}")

        idx = rw.AddAtom(_make_rdkit_atom_from_symbol(str(element)))
        id_to_idx[atom_id] = idx

    seen_charge_atom_ids = set()
    for charge_obj in charges:
        if not isinstance(charge_obj, dict):
            raise ValueError("charges entries must be objects")
        atom_id = charge_obj.get("atom_id")
        formal_charge = charge_obj.get("formal_charge")

        if not isinstance(atom_id, str):
            raise ValueError(
                f"charges.atom_id must be a string. Got: {type(atom_id)}"
            )
        if atom_id not in id_to_idx:
            raise ValueError(f"charges.atom_id references unknown atom id: {atom_id}")
        if not isinstance(formal_charge, int):
            raise ValueError(
                f"charges.formal_charge must be int. Got: {type(formal_charge)}"
            )
        if formal_charge == 0:
            continue
        if formal_charge < -5 or formal_charge > 5:
            raise ValueError(
                "charges.formal_charge out of supported range [-5,5]: "
                f"{formal_charge}"
            )
        if atom_id in seen_charge_atom_ids:
            raise ValueError(f"Duplicate charges entry for atom_id: {atom_id}")
        seen_charge_atom_ids.add(atom_id)
        rw.GetAtomWithIdx(id_to_idx[atom_id]).SetFormalCharge(formal_charge)

    seen_edges: Dict[Tuple[int, int], float] = {}
    for bond_obj in bonds:
        if not isinstance(bond_obj, dict):
            raise ValueError("Each bond must be an object")
        a1 = bond_obj.get("source")
        a2 = bond_obj.get("target")
        order_raw = bond_obj.get("order")

        if not isinstance(a1, str) or not isinstance(a2, str):
            raise ValueError("Bond source/target must be strings")
        if a1 not in id_to_idx or a2 not in id_to_idx:
            raise ValueError(f"Bond references unknown atom id(s): {a1}, {a2}")

        i = id_to_idx[a1]
        j = id_to_idx[a2]
        if i == j:
            raise ValueError(f"Self-bonds are not supported: {a1} - {a2}")

        order = _normalize_bond_order(order_raw)
        key = (i, j) if i < j else (j, i)
        if key in seen_edges:
            prev = seen_edges[key]
            if abs(prev - order) < 1e-9:
                continue
            raise ValueError(
                f"Conflicting duplicated edge between {a1} and {a2}: "
                f"previous order={prev}, new order={order}"
            )

        seen_edges[key] = order
        rw.AddBond(key[0], key[1], _ORDER_TO_BONDTYPE[order])

    mol = rw.GetMol()
    _infer_and_mark_aromatic_atoms(mol)
    _apply_aromatic_n_h(mol, aromatic_n_h, id_to_idx)
    Chem.SanitizeMol(mol)
    return mol


def MolToJSON(
    mol: Chem.Mol,
    *,
    atom_id_style: str = "element",
    include_empty_fields: bool = False,
) -> Dict[str, Any]:
    """
    Convert an RDKit molecule to MolJSON.

    The input molecule is sanitized before conversion and explicit hydrogen atoms
    are omitted from the serialized MolJSON representation.

    atom_id_style controls how atom identifiers are assigned:
    - "element": element-based identifiers such as C1 and N1
    - "a": sequential identifiers such as a1 and a2

    If include_empty_fields is False, empty charges and aromatic_n_h fields are
    omitted. If True, they are emitted as null.
    """
    if mol is None:
        raise ValueError("mol is None")
    if atom_id_style not in ("element", "a"):
        raise ValueError("atom_id_style must be 'element' or 'a'")

    m = Chem.Mol(mol)
    Chem.SanitizeMol(m)

    kept_idxs = [atom.GetIdx() for atom in m.GetAtoms() if atom.GetSymbol() != "H"]
    kept_set = set(kept_idxs)

    idx_to_id: Dict[int, str] = {}
    if atom_id_style == "a":
        for n, idx in enumerate(kept_idxs, start=1):
            idx_to_id[idx] = f"a{n}"
    else:
        element_counts: Dict[str, int] = {}
        for idx in kept_idxs:
            sym = m.GetAtomWithIdx(idx).GetSymbol()
            element_counts[sym] = element_counts.get(sym, 0) + 1
            idx_to_id[idx] = f"{sym}{element_counts[sym]}"

    atoms: List[Dict[str, Any]] = []
    for idx in kept_idxs:
        atom = m.GetAtomWithIdx(idx)
        sym = atom.GetSymbol()
        if not _is_valid_element_symbol(sym):
            raise ValueError(f"Invalid element symbol in RDKit molecule: {sym!r}")
        atoms.append({"id": idx_to_id[idx], "element": sym})

    bonds: List[Dict[str, Any]] = []
    for bond in m.GetBonds():
        i = bond.GetBeginAtomIdx()
        j = bond.GetEndAtomIdx()
        if i not in kept_set or j not in kept_set:
            continue
        bt = bond.GetBondType()
        if bt not in _BONDTYPE_TO_ORDER:
            raise ValueError(f"Unsupported bond type for this MolJSON schema: {bt}")
        bonds.append(
            {
                "source": idx_to_id[i],
                "target": idx_to_id[j],
                "order": _BONDTYPE_TO_ORDER[bt],
            }
        )

    charges: List[Dict[str, Any]] = []
    for idx in kept_idxs:
        fc = int(m.GetAtomWithIdx(idx).GetFormalCharge())
        if fc != 0:
            charges.append({"atom_id": idx_to_id[idx], "formal_charge": fc})

    aromatic_n_h: List[Dict[str, Any]] = []
    for idx in kept_idxs:
        atom = m.GetAtomWithIdx(idx)
        if atom.GetSymbol() != "N":
            continue
        if not atom.GetIsAromatic():
            continue
        hcount = int(atom.GetTotalNumHs())
        if hcount > 0:
            if hcount != 1:
                raise ValueError(
                    f"MolToJSON only supports aromatic_n_h.hcount=1. Got: {hcount}"
                )
            aromatic_n_h.append({"atom_id": idx_to_id[idx], "hcount": hcount})

    moljson: Dict[str, Any] = {
        "atoms": atoms,
        "bonds": bonds,
        "charges": charges,
        "aromatic_n_h": aromatic_n_h,
    }

    for key in ("charges", "aromatic_n_h"):
        if key in moljson and isinstance(moljson[key], list) and len(moljson[key]) == 0:
            if include_empty_fields:
                moljson[key] = None
            else:
                moljson.pop(key, None)

    return moljson


def _canonical_smiles_no_stereo(mol: Chem.Mol) -> str:
    m = Chem.Mol(mol)
    Chem.SanitizeMol(m)
    return Chem.MolToSmiles(m, canonical=True, isomericSmiles=False)


def CheckRoundTrip(
    mol: Chem.Mol, *, atom_id_style: str = "element"
) -> Tuple[bool, str, str, Dict[str, Any]]:
    """
    Round trip check:
    RDKit Mol -> MolJSON -> RDKit Mol

    Returns:
    - ok: bool
    - input_smiles_no_stereo: str
    - roundtrip_smiles_no_stereo: str
    - moljson: dict
    """
    input_smiles = _canonical_smiles_no_stereo(mol)
    moljson = MolToJSON(mol, atom_id_style=atom_id_style)
    mol2 = MolFromJSON(moljson)
    output_smiles = _canonical_smiles_no_stereo(mol2)
    return (input_smiles == output_smiles), input_smiles, output_smiles, moljson
