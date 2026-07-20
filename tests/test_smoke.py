import unittest

from rdkit import Chem

from moljson import CheckRoundTrip, GetPaperSchema, GetSchema


class MolJSONSmokeTests(unittest.TestCase):
    def test_schemas_are_independent_objects(self) -> None:
        schema = GetSchema()
        paper_schema = GetPaperSchema()

        self.assertEqual(schema["type"], "object")
        self.assertEqual(paper_schema["type"], "object")
        self.assertIsNot(schema, GetSchema())

    def test_rdkit_round_trip(self) -> None:
        molecule = Chem.MolFromSmiles("c1c[nH]cc1")
        self.assertIsNotNone(molecule)

        ok, input_smiles, output_smiles, _ = CheckRoundTrip(molecule)

        self.assertTrue(ok, msg=f"{input_smiles} != {output_smiles}")


if __name__ == "__main__":
    unittest.main()
