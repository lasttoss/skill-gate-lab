import json
import os
import unittest

from gate import report, tier1, tier2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ReportTest(unittest.TestCase):
    def setUp(self):
        docs, _ = tier1.load_catalog(ROOT)
        self.first = tier1.run(ROOT)
        self.second = tier2.run(ROOT, docs)
        self.summary = {
            "rows": 18, "passed": 16, "failed": 2, "pass_rate": 88.9,
            "cost_usd": 0.001524, "p50_ms": 99.0, "p95_ms": 198.0,
            "stability_pct": 100.0, "runs_per_input": 2, "model": "replay-1",
            "per_step": [{"step_id": "reproduce", "skill": "test-first", "passed": 4,
                          "failed": 2, "reasons": {"budget_exceeded": 2},
                          "pass_rate": 66.7, "p50_ms": 99.0, "p95_ms": 198.0}],
            "failures": [{"input_id": "bug-huge-log", "step_id": "reproduce",
                          "reason_codes": ["budget_exceeded"], "trace": "…"}],
        }

    def test_html_is_self_contained(self):
        document = report.to_json(self.first, self.second, self.summary, {"rank1_floor": 100.0})
        page = report.to_html(document)
        self.assertIn("<html", page)
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertIn("88.9%", page)
        self.assertIn("budget_exceeded", page)

    def test_json_round_trips(self):
        document = report.to_json(self.first, self.second, self.summary, {"rank1_floor": 100.0})
        self.assertEqual(json.loads(json.dumps(document))["tier2"]["rank1_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
