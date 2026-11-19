import json
import os
import tempfile
import unittest

from gate import reasons, tier1, tier2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ReasonsTest(unittest.TestCase):
    def test_every_code_is_closed(self):
        self.assertEqual(len(reasons.CODES), 8)

    def test_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            reasons.check("made_up")


class Tier1Test(unittest.TestCase):
    def test_real_catalog_is_clean(self):
        result = tier1.run(ROOT)
        self.assertTrue(result["passed"], result["findings"])
        self.assertEqual(result["skills"], 5)

    def test_broken_skill_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "catalog", "broken"))
            path = os.path.join(tmp, "catalog", "broken", "SKILL.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("---\nname: broken\ndescription: short\ntags: []\n---\n## Steps\n1. x\n")
            findings = tier1.run(tmp)["findings"]
            codes = {f["code"] for f in findings}
            self.assertIn("missing_section", codes)
            self.assertIn("bad_version", codes)
            self.assertIn("description_length", codes)
            self.assertIn("missing_tags", codes)

    def test_missing_skill_md_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "catalog", "empty"))
            codes = {f["code"] for f in tier1.run(tmp)["findings"]}
            self.assertIn("missing_skill_md", codes)


class Tier2Test(unittest.TestCase):
    def setUp(self):
        self.docs, _ = tier1.load_catalog(ROOT)

    def test_real_routing_is_perfect(self):
        result = tier2.run(ROOT, self.docs)
        self.assertTrue(result["passed"], result["findings"])
        self.assertEqual(result["rank1_rate"], 100.0)

    def test_missing_dependency_is_caught(self):
        flow = {"name": "f", "steps": [
            {"id": "a", "skill": "code-review", "needs": {"ghost": ["x"]}}]}
        codes = {f["code"] for f in tier2.check_workflow(flow, self.docs)}
        self.assertIn("missing_dependency", codes)

    def test_overlap_is_caught(self):
        flow = {"name": "f", "steps": [
            {"id": "a", "skill": "code-review", "writes": {"art": ["x"]}},
            {"id": "b", "skill": "release-notes", "needs": {"art": ["x"]}, "writes": {"art": ["y"]}}]}
        codes = {f["code"] for f in tier2.check_workflow(flow, self.docs)}
        self.assertIn("overlap", codes)

    def test_contract_gap_is_caught(self):
        flow = {"name": "f", "steps": [
            {"id": "a", "skill": "code-review", "writes": {"art": ["x"]}},
            {"id": "b", "skill": "release-notes", "needs": {"art": ["x", "y"]}}]}
        codes = {f["code"] for f in tier2.check_workflow(flow, self.docs)}
        self.assertIn("contract_gap", codes)

    def test_unknown_skill_is_caught(self):
        flow = {"name": "f", "steps": [{"id": "a", "skill": "nope"}]}
        codes = {f["code"] for f in tier2.check_workflow(flow, self.docs)}
        self.assertIn("unknown_skill", codes)


if __name__ == "__main__":
    unittest.main()
