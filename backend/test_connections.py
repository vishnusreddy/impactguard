import unittest, os
from unittest.mock import patch
from engine import Engine
from connections import state, configure, collect, analyze, connect
from security import redact, safe_file
from investigator import investigate


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine(":memory:")

    def tearDown(self):
        self.e.db.close()

    def test_multiple_repos_and_reset(self):
        with patch("github_integration.fetch_commits", return_value=[]):
            connect(self.e, "one/frontend")
            connect(self.e, "one/backend")
            connect(self.e, "one/frontend")
        self.assertEqual(len(state(self.e)["repos"]), 2)
        self.e.reset()
        self.assertEqual(len(state(self.e)["repos"]), 2)

    def test_config_validation(self):
        for body in (
            {"shopify_store": "evil.com"},
            {"ga_property": "../42"},
            {"policy": "x" * 1501},
        ):
            with self.assertRaises(ValueError):
                configure(self.e, body)

    def test_samples_and_analysis(self):
        for source in ("shopify", "analytics"):
            result = collect(self.e, {"source": source, "sample": True})
            self.assertEqual(len(result["snapshots"][source]["rows"]), 14)
            with patch.dict(os.environ, {}, clear=True):
                result = analyze(self.e, {"source": source})
            self.assertEqual(result["classification"], "inconclusive")
            self.assertEqual(result["mode"], "synthetic")

    def test_credentials_not_in_state(self):
        with patch.dict(os.environ, {"IMPACTGUARD_SHOPIFY_TOKEN": "shpat_" + "x" * 32}):
            self.assertNotIn("shpat_", str(state(self.e)))

    def test_redaction(self):
        secret = "ghp_" + "a" * 36
        self.assertNotIn(
            secret, str(redact({"patch": "token=" + secret, "password": "anything"}))
        )
        self.assertFalse(safe_file(".env.production"))
        self.assertFalse(safe_file("config/application_default_credentials.json"))
        self.assertFalse(safe_file(".local/runtime.env"))
        self.assertFalse(safe_file("config/service-account.json"))
        self.assertTrue(safe_file("src/payment.ts"))

    def test_no_ambient_cloud(self):
        with patch.dict(
            os.environ, {"GCP_PROJECT": "work", "CLOUD_ENABLED": "1"}, clear=True
        ):
            self.assertEqual(
                investigate({"summary": "Observed decline"})["provider"],
                "Deterministic analysis",
            )

    def test_manual_review_preserves_events(self):
        f = self.e.launch("checkout")["finding"]
        n = self.e.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        for action, status in [
            ("ignore", "ignored"),
            ("not_issue", "not_issue"),
            ("reopen", "active"),
            ("resolve", "resolved"),
        ]:
            self.e.action(action, f["id"])
            self.assertEqual(self.e.finding(f["id"])["status"], status)
        self.assertEqual(
            self.e.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], n
        )

    def test_non_regression_samples(self):
        for case, category in [
            ("traffic", "traffic_anomaly"),
            ("security", "security_signal"),
            ("data_quality", "data_quality"),
        ]:
            collect(self.e, {"source": "analytics", "sample": True, "scenario": case})
            with patch.dict(os.environ, {}, clear=True):
                result = analyze(self.e, {"source": "analytics"})
            self.assertEqual(result["classification"], category)

    def test_shopify_no_customer_fields(self):
        from connections import shopify
        import json

        payload = {
            "data": {
                "orders": {
                    "nodes": [
                        {
                            "createdAt": "2026-10-11T00:00:00Z",
                            "displayFinancialStatus": "PAID",
                            "totalPriceSet": {
                                "shopMoney": {"amount": "82.00", "currencyCode": "USD"}
                            },
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }
        from io import BytesIO

        with patch.dict(
            os.environ, {"IMPACTGUARD_SHOPIFY_TOKEN": "private-token"}
        ), patch(
            "urllib.request.urlopen", return_value=BytesIO(json.dumps(payload).encode())
        ) as call:
            data = shopify({"shopify_store": "example.myshopify.com"})
        request = call.call_args.args[0]
        self.assertNotIn("private-token", request.data.decode())
        self.assertNotIn("customer", request.data.decode())
        self.assertEqual(data["rows"][0]["currency"], "USD")

    def test_source_review_preserves_snapshot(self):
        from connections import review_source
        import copy

        collect(self.e, {"source": "analytics", "sample": True, "scenario": "traffic"})
        original = copy.deepcopy(state(self.e)["snapshots"])
        with patch.dict(os.environ, {}, clear=True):
            finding = analyze(self.e, {"source": "analytics"})
        review_source(self.e, {"finding_id": finding["id"], "action": "resolve"})
        self.assertEqual(state(self.e)["findings"][0]["status"], "resolved")
        self.assertEqual(state(self.e)["snapshots"], original)

    def test_concurrent_dashboard_and_connection_state(self):
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(
                    lambda i: self.e.dashboard() if i % 2 else state(self.e), range(40)
                )
            )
        self.assertEqual(len(results), 40)

    def test_ai_receives_normalized_source_windows(self):
        collect(self.e, {"source": "analytics", "sample": True})
        with patch(
            "investigator.investigate",
            return_value={
                "classification": "inconclusive",
                "provider": "test",
                "summary": "Observed change",
            },
        ) as call:
            analyze(self.e, {"source": "analytics"})
        evidence = call.call_args.args[0]
        self.assertNotIn("sessions", evidence["baseline"])
        self.assertNotIn("orders", evidence["actual"])
        self.assertGreater(
            evidence["actual"]["mean_daily_sessions"],
            evidence["baseline"]["mean_daily_sessions"],
        )
        self.assertLess(
            evidence["actual"]["completion_rate"],
            evidence["baseline"]["completion_rate"],
        )

    def test_repeated_analysis_retains_review_state(self):
        from connections import review_source

        collect(self.e, {"source": "analytics", "sample": True})
        with patch.dict(os.environ, {}, clear=True):
            first = analyze(self.e, {"source": "analytics"})
            review_source(self.e, {"finding_id": first["id"], "action": "ignore"})
            second = analyze(self.e, {"source": "analytics"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["status"], "ignored")
        self.assertTrue(second["cached"])
        self.assertEqual(len(state(self.e)["findings"]), 1)
