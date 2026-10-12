import base64, copy, unittest
from unittest.mock import patch
from engine import Engine
from metric_discovery import assess, connector_inventory, discover, sample_evidence
from github_integration import fetch_business_context


class MetricDiscoveryTests(unittest.TestCase):
    def result(self):
        return {
            "provider": "Vertex AI test",
            "business_summary": "Storefront",
            "metrics": [
                {
                    "name": "Revenue per session",
                    "priority": "high",
                    "business_question": "Did sales yield change?",
                    "definition": "Daily revenue / sessions, excluding test orders; confirm currency.",
                    "required_fields": ["revenue", "sessions"],
                    "readiness": "available_aggregate",
                    "evidence_refs": [{"id": "connector:analytics", "line": 0}],
                    "limitations": "Currency is not collected",
                    "sql_draft": "",
                }
            ],
            "logging": [
                {
                    "event_name": "payment_status_changed",
                    "when_to_emit": "After recording authoritative status",
                    "fields": ["event_id", "order_id", "status", "release_sha"],
                    "purpose": "Track settlement changes",
                    "deduplication": "Stable event ID",
                    "evidence_refs": [{"id": "code:1", "line": 3}],
                }
            ],
            "questions": ["Which currency is used?"],
        }

    def test_valid_proposal_does_not_enable_metrics(self):
        e = Engine(":memory:")
        before = e.stats("live")
        with patch("metric_discovery._request", return_value=self.result()):
            r = discover(e, {"sample": True})
        self.assertEqual(r["status"], "proposed")
        self.assertEqual(before, e.stats("live"))
        self.assertIsNone(e.get("enabled_metrics"))
        e.db.close()

    def test_invalid_reference_rejected(self):
        for ref in ({"id": "unknown", "line": 0}, {"id": "code:1", "line": 999}):
            r = self.result()
            r["logging"][0]["evidence_refs"] = [ref]
            with patch("metric_discovery._request", return_value=r), self.assertRaises(
                ValueError
            ):
                assess(sample_evidence())

    def test_connector_inventory_never_includes_row_values(self):
        inventory = connector_inventory(
            {
                "analytics": {
                    "mode": "live",
                    "rows": [
                        {
                            "email": "private@example.com",
                            "sessions": 8301,
                            "credentials": {"token": "secret"},
                        }
                    ],
                }
            }
        )
        self.assertNotIn("private@example.com", str(inventory))
        self.assertNotIn("8301", str(inventory))
        self.assertNotIn("secret", str(inventory))

    def test_offline_assessment_has_no_invented_metrics(self):
        with patch("metric_discovery._request", return_value=None):
            r = assess(sample_evidence())
        self.assertEqual(r["status"], "unassessed")
        self.assertEqual(r["metrics"], [])

    def test_same_assessment_is_durably_cached(self):
        e = Engine(":memory:")
        with patch("metric_discovery._request", return_value=self.result()) as call:
            discover(e, {"sample": True})
            r = discover(e, {"sample": True})
            self.assertEqual(call.call_count, 1)
            self.assertTrue(r["cached"])
        e.db.close()

    def test_snapshot_excludes_secret_files_and_redacts_code(self):
        tree = {
            "tree": [
                {
                    "path": ".env",
                    "type": "blob",
                    "mode": "100644",
                    "size": 10,
                    "sha": "b" * 40,
                },
                {
                    "path": "src/payment.ts",
                    "type": "blob",
                    "mode": "100644",
                    "size": 100,
                    "sha": "c" * 40,
                },
                {
                    "path": "node_modules/payment.ts",
                    "type": "blob",
                    "mode": "100644",
                    "size": 10,
                    "sha": "d" * 40,
                },
            ]
        }
        secret = "ghp_" + "x" * 36
        blob = {
            "encoding": "base64",
            "size": 100,
            "content": base64.b64encode(
                ('const key="' + secret + '";\nrecordPayment(status);').encode()
            ).decode(),
        }
        with patch("github_integration.github_get", side_effect=[tree, blob]) as get:
            r = fetch_business_context("demo/store", "a" * 40)
        self.assertEqual(len(r["files"]), 1)
        self.assertNotIn(secret, str(r))
        self.assertEqual(get.call_count, 2)

    def test_sql_is_omitted_without_database_schema(self):
        r = self.result()
        r["metrics"][0]["sql_draft"] = "SELECT * FROM invented_table"
        with patch("metric_discovery._request", return_value=r):
            result = assess(sample_evidence())
        self.assertEqual(result["metrics"][0]["sql_draft"], "")
        self.assertIn("no database schema", result["metrics"][0]["limitations"])

    def test_sensitive_logging_fields_rejected(self):
        r = self.result()
        r["logging"][0]["fields"] = ["card_number"]
        with patch("metric_discovery._request", return_value=r), self.assertRaises(
            ValueError
        ):
            assess(sample_evidence())

    def test_no_sources_requires_collection(self):
        e = Engine(":memory:")
        with self.assertRaises(ValueError):
            discover(e, {})
        e.db.close()


if __name__ == "__main__":
    unittest.main()
