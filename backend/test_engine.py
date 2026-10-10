import unittest
from engine import Engine


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine(":memory:")

    def tearDown(self):
        self.e.db.close()

    def test_checkout_detection_and_recovery(self):
        d = self.e.launch("checkout")
        f = d["finding"]
        self.assertGreater(f["z_score"], 5)
        self.assertGreater(f["exposure"], 0)
        self.assertGreater(
            f["segments"][0]["baseline"] - f["segments"][0]["actual"], 0.25
        )
        expected = (f["baseline"]["conversion"] - f["actual"]["conversion"]) * 120 * 82
        self.assertAlmostEqual(f["exposure"], expected, delta=1)
        d = self.e.action("recover")
        self.assertEqual(d["status"], "recovered")
        self.assertAlmostEqual(
            d["metrics"]["conversion"], d["baseline"]["conversion"], delta=0.025
        )
        with self.assertRaises(ValueError):
            self.e.action("recover")

    def test_promotion_negative_margin(self):
        f = self.e.launch("promotion")["finding"]
        self.assertGreater(f["exposure"], 0)
        self.assertEqual(f["unit"], "week")

    def test_delivery_cohorts(self):
        f = self.e.launch("delivery")["finding"]
        self.assertGreater(f["relative_change"], 20)
        self.assertEqual(f["unit"], "year")

    def test_events_idempotency_and_validation(self):
        e = {
            "event_id": "once",
            "timestamp": "2026-10-10T14:00:00Z",
            "source": "checkout",
            "event_type": "checkout_completed",
            "session_id": "S1",
            "amount": 82,
        }
        self.e.ingest(e)
        self.e.ingest(e)
        self.assertEqual(
            self.e.db.execute("SELECT COUNT(*) FROM events WHERE id='once'").fetchone()[
                0
            ],
            1,
        )
        with self.assertRaises(ValueError):
            self.e.ingest({})
        with self.assertRaises(ValueError):
            self.e.ingest({**e, "timestamp": "2026-10-10T14:00:00"})
        with self.assertRaises(ValueError):
            self.e.ingest({**e, "timestamp": 123})
        with self.assertRaises(ValueError):
            self.e.ingest({**e, "amount": float("nan")})

    def test_banking_reconciliation_preserves_postings(self):
        f = self.e.launch("banking")["finding"]
        self.assertEqual(self.e.bank_summary()["mismatches"], 200)
        self.assertGreater(f["exposure"], 0)
        self.assertEqual(f["commits"][0]["sha"][:7], "e921bd0")
        self.e.action("recover")
        b = self.e.bank_summary()
        self.assertEqual(b["mismatches"], 0)
        self.assertEqual(b["reversals"], 200)
        self.assertEqual(
            self.e.db.execute(
                "SELECT COUNT(*) FROM ledger WHERE kind='credit'"
            ).fetchone()[0],
            2000,
        )
        net = self.e.db.execute(
            "SELECT SUM(l.amount_cents) FROM ledger l JOIN bank_transactions t ON t.id=l.transaction_id WHERE t.bank_status!='settled'"
        ).fetchone()[0]
        self.assertAlmostEqual(net, 0, places=6)

    def test_reconciliation_detects_duplicate_and_missing_postings(self):
        self.e.launch("banking")
        tx = self.e.db.execute(
            "SELECT id,amount_cents FROM bank_transactions WHERE bank_status='settled' LIMIT 1"
        ).fetchone()
        self.e.db.execute(
            "INSERT INTO ledger VALUES ('duplicate',?,?, 'credit','2026-10-10')",
            (tx["id"], tx["amount_cents"]),
        )
        self.e.db.execute(
            "INSERT INTO bank_transactions VALUES ('missing','2026-10-10','settled','success',1000)"
        )
        self.assertEqual(self.e.bank_summary()["mismatches"], 202)
        self.assertEqual(self.e.bank_summary()["missing_credits"], 10)
        self.e.action("recover")
        self.assertEqual(self.e.bank_summary()["mismatches"], 0)
        self.assertEqual(self.e.bank_summary()["missing_credits"], 0)
        self.assertEqual(
            self.e.db.execute(
                "SELECT COUNT(*) FROM ledger WHERE id='duplicate'"
            ).fetchone()[0],
            1,
        )

    def test_reset_and_active_guard(self):
        self.e.launch("checkout")
        with self.assertRaises(ValueError):
            self.e.launch("promotion")
        self.assertEqual(self.e.reset()["status"], "healthy")
