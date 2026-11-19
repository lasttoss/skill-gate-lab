import json
import os
import unittest

from gate import tier3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _flow():
    with open(os.path.join(ROOT, "cases", "workflows", "coding-flow.json"), encoding="utf-8") as handle:
        return json.load(handle)


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.executor = tier3.ReplayExecutor(tier3.load_prices(ROOT))

    def test_same_input_same_numbers(self):
        first = self.executor.call("hello world", {"step_id": "s1"})
        second = self.executor.call("hello world", {"step_id": "s1"})
        self.assertEqual(first["tokens_in"], second["tokens_in"])
        self.assertEqual(first["latency_ms"], second["latency_ms"])
        self.assertFalse(first["truncated"])

    def test_budget_marks_truncated(self):
        answer = self.executor.call("word " * 400, {"step_id": "s1", "token_budget": 10})
        self.assertTrue(answer["truncated"])


class JudgeTest(unittest.TestCase):
    def _codes(self, step, answer):
        found = []
        status = tier3._judge(step, answer, found)
        return status, sorted(set(found))

    def test_empty_output(self):
        status, codes = self._codes({"expect": {}}, {"text": "   "})
        self.assertEqual((status, codes), ("failed", ["empty"]))

    def test_missing_schema_field(self):
        status, codes = self._codes({"expect": {"schema": ["verdict"]}}, {"text": '{"other": 1}'})
        self.assertEqual(status, "failed")
        self.assertIn("format_invalid", codes)

    def test_must_contain(self):
        status, _ = self._codes({"expect": {"must_contain": ["bug"]}}, {"text": "a bug here"})
        self.assertEqual(status, "passed")

    def test_must_not_contain_is_hallucination(self):
        status, codes = self._codes({"expect": {"must_not_contain": ["invented"]}},
                                    {"text": "an invented claim"})
        self.assertIn("hallucinated", codes)

    def test_timeout(self):
        status, codes = self._codes({}, {"text": "", "timeout": True})
        self.assertEqual((status, codes), ("failed", ["timeout"]))

    def test_error_status(self):
        status, codes = self._codes({}, {"text": "x", "error": "boom"})
        self.assertEqual((status, codes), ("error", ["error"]))


class RunTest(unittest.TestCase):
    def test_smoke_run_shape(self):
        result = tier3.run(ROOT, _flow(), tier3.ReplayExecutor(tier3.load_prices(ROOT)), runs=2)
        summary = result["summary"]
        self.assertEqual(summary["rows"], 18)          # 3 inputs x 2 runs x 3 steps
        self.assertEqual(summary["runs_per_input"], 2)
        self.assertLess(summary["pass_rate"], 100.0)   # the oversized input must fail
        self.assertEqual(summary["stability_pct"], 100.0)
        self.assertEqual(len(summary["per_step"]), 3)
        self.assertGreater(summary["cost_usd"], 0.0)
        self.assertGreaterEqual(summary["p95_ms"], summary["p50_ms"])
        codes = {code for step in summary["per_step"] for code in step["reasons"]}
        self.assertIn("budget_exceeded", codes)

    def test_command_executor(self):
        executor = tier3.CommandExecutor("cat")
        answer = executor.call("piped through", {})
        self.assertEqual(answer["text"], "piped through")


if __name__ == "__main__":
    unittest.main()
