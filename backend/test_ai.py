import os, unittest
from unittest.mock import patch
from investigator import detect_anomaly, investigate, diff_lines, evidence_for


class AITests(unittest.TestCase):
    def setUp(self):
        self.finding = {
            "metric": "Settlement consistency",
            "scenario": "banking",
            "observations": [{"id": "e1", "expected": False, "actual": True}],
            "deployment_mapping": {"kind": "fixture"},
            "commits": [
                {
                    "sha": "a" * 40,
                    "deployment_eligible": True,
                    "files": [
                        {
                            "filename": "src/bank.py",
                            "patch": '@@ -40,2 +40,2 @@\n def eligible(status):\n-    return status == "settled"\n+    return True',
                        }
                    ],
                }
            ],
        }

    def result(self):
        return {
            "suspect_commit_sha": "a" * 40,
            "file": "src/bank.py",
            "line": 41,
            "defect_explanation": "Unconditional success credits failed transfers.",
            "summary": "Status validation was removed.",
            "recommended_verification": "Test failed and pending statuses.",
            "ruled_out_commits": [],
            "suggested_fix_diff": '--- a/src/bank.py\n+++ b/src/bank.py\n@@ -41 +41 @@\n-    return True\n+    return status == "settled"',
            "guard_test_diff": '--- /dev/null\n+++ b/tests/test_bank.py\n@@ -0,0 +1 @@\n+assert eligible("failed") is False',
            "provider": "mock Gemini",
        }

    def decision(self):
        return {
            "provider": "mock Gemini",
            "detected": True,
            "classification": "business_regression",
            "summary": "Failed transfers received credits.",
            "reason": "Observed outcome violates settlement evidence.",
            "evidence_refs": ["e1"],
            "accounts_review": [],
        }

    def test_model_makes_decision_without_rule_threshold(self):
        with patch("investigator._request", return_value=self.decision()) as call:
            r = detect_anomaly(self.finding)
        self.assertTrue(r["detected"])
        self.assertNotIn("classification", call.call_args.args[1])

    def test_no_ai_does_not_fabricate_rule_decision(self):
        with patch.dict(os.environ, {}, clear=True):
            r = detect_anomaly(self.finding)
        self.assertIsNone(r["detected"])
        self.assertEqual(r["provider"], "AI unavailable")

    def test_valid_reference_and_unapplied_drafts(self):
        with patch("investigator._request", return_value=self.result()):
            r = investigate(self.finding)
        self.assertEqual(r["attribution_status"], "validated_reference")
        self.assertIn("not applied", r["draft_status"])

    def test_unknown_sha_file_line_and_undeployed_rejected(self):
        for key, value in [
            ("suspect_commit_sha", "b" * 40),
            ("file", "missing.py"),
            ("line", 900),
        ]:
            r = self.result()
            r[key] = value
            with patch("investigator._request", return_value=r), self.assertRaises(
                ValueError
            ):
                investigate(self.finding)
        self.finding["commits"][0]["deployment_eligible"] = False
        with patch(
            "investigator._request", return_value=self.result()
        ), self.assertRaises(ValueError):
            investigate(self.finding)

    def test_unknown_evidence_rejected(self):
        r = self.decision()
        r["evidence_refs"] = ["invented"]
        with patch("investigator._request", return_value=r), self.assertRaises(
            ValueError
        ):
            detect_anomaly(self.finding)

    def test_account_evidence_cannot_cross_accounts(self):
        self.finding["bank_accounts"] = [
            {"account_id": "acct_a", "transaction_ids": ["tx1"]}
        ]
        r = self.decision()
        r["accounts_review"] = [
            {
                "account_id": "acct_a",
                "flag_for_review": True,
                "reason": "Repeated credits",
                "transaction_ids": ["other-account-tx"],
            }
        ]
        with patch("investigator._request", return_value=r), self.assertRaises(
            ValueError
        ):
            detect_anomaly(self.finding)

    def test_bank_does_not_receive_unrelated_commerce_totals(self):
        self.finding.update(
            baseline={"conversion": 0.7, "n": 30000},
            actual={"conversion": 0.6, "n": 6000},
        )
        e = evidence_for(self.finding)
        self.assertNotIn("baseline", e)
        self.assertNotIn("actual", e)

    def test_healthy_verdict_allowed_and_not_overridden(self):
        r = self.decision()
        r.update(detected=False, classification="healthy", evidence_refs=[])
        with patch("investigator._request", return_value=r):
            self.assertFalse(detect_anomaly(self.finding)["detected"])

    def test_contradictory_decision_rejected(self):
        r = self.decision()
        r["classification"] = "healthy"
        with patch("investigator._request", return_value=r), self.assertRaises(
            ValueError
        ):
            detect_anomaly(self.finding)

    def test_unknown_deployment_is_not_causal_attribution(self):
        self.finding["deployment_mapping"] = None
        with patch("investigator._request", return_value=self.decision()):
            r = detect_anomaly(self.finding)
        self.assertEqual(r["classification"], "inconclusive")
        self.assertTrue(r["detected"])

    def test_unsafe_draft_rejected(self):
        r = self.result()
        r["suggested_fix_diff"] = (
            "--- a/src/bank.py\n+++ b/../../credentials.json\n@@ -1 +1 @@\n+x"
        )
        with patch("investigator._request", return_value=r), self.assertRaises(
            ValueError
        ):
            investigate(self.finding)

    def test_invalid_draft_does_not_erase_valid_code_reference(self):
        r = self.result()
        r["guard_test_diff"] = "not a diff"
        with patch("investigator._request", return_value=r):
            r = investigate(self.finding)
        self.assertEqual(r["attribution_status"], "validated_reference")
        self.assertEqual(r["guard_test_diff"], "")

    def test_diff_line_numbers(self):
        self.assertEqual(
            diff_lines(self.finding["commits"][0]["files"][0]["patch"])[-1]["line"], 41
        )
