"""Unit tests for rules and merge layers."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from merge import (  # noqa: E402
    merge_audit,
    merge_warnings,
    recompute_overall,
    viewer_payload,
)
from prompts import FEW_SHOT_ASSISTANT  # noqa: E402
from rules import run_rules  # noqa: E402


class MergeTests(unittest.TestCase):
    def test_recompute_overall_no_cap(self):
        dims = [{"key": "hook", "score": 2}, {"key": "clarity", "score": 3}]
        self.assertEqual(recompute_overall(dims, []), 50)

    def test_recompute_overall_with_cap(self):
        dims = [{"key": "hook", "score": 4}, {"key": "clarity", "score": 4}]
        self.assertEqual(recompute_overall(dims, ["GOAL_ACTION_MISMATCH"]), 39)

    def test_merge_rule_overwrites_llm_same_code(self):
        llm = [{"code": "NO_DEADLINE", "severity": "info", "source": "llm", "message": "a"}]
        rule = [{"code": "NO_DEADLINE", "severity": "warning", "source": "rule", "message": "b"}]
        merged = merge_warnings(llm, rule)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["severity"], "warning")
        self.assertEqual(merged[0]["source"], "rule")

    def test_merge_few_shot_with_rules(self):
        llm_payload = json.loads(FEW_SHOT_ASSISTANT)
        post = (
            "Webinar on product metrics 🚀🚀 Link in bio!!! "
            "#product #metrics #growth #pm #webinar #training #analytics"
        )
        rule_warnings = run_rules("telegram", "Register for Thu 7pm webinar", "PMs", post)
        codes = {w["code"] for w in rule_warnings}
        self.assertIn("HASHTAG_STUFFING", codes)
        self.assertIn("NO_DEADLINE", codes)

        merged = merge_audit(llm_payload, rule_warnings)
        audit = merged["auditReport"]
        self.assertIsNotNone(audit)
        self.assertIn("GOAL_ACTION_MISMATCH", audit["goalAlignment"]["cappedBy"])
        self.assertLessEqual(audit["goalAlignment"]["overall"], 39)

        view = viewer_payload(merged)
        self.assertIn("goalAlignment", view)
        self.assertTrue(any(w["source"] == "rule" for w in view["warnings"]))


class RulesTests(unittest.TestCase):
    def test_hashtag_stuffing_telegram(self):
        post = "#a #b #c #d"
        warnings = run_rules("telegram", "Grow audience", "Devs", post)
        self.assertTrue(any(w["code"] == "HASHTAG_STUFFING" for w in warnings))

    def test_chat_dump_format(self):
        post = "[6/5/26 5:10 PM] Alex: hello team"
        warnings = run_rules("telegram", "Notify team", "Team", post)
        self.assertTrue(any(w["code"] == "CHAT_DUMP_FORMAT" for w in warnings))


if __name__ == "__main__":
    unittest.main()
