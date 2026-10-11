"""Persisted business measurements with explicit Gemini anomaly decisions."""

from messages import format_finding
import json, math, os, random, sqlite3, threading, uuid
from datetime import datetime, timedelta, timezone

LOCK = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


class Engine:
    def __init__(self, path=None):
        path = path or os.getenv("DATABASE_PATH", ".data/impactguard.db")
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, timestamp TEXT, phase TEXT, browser TEXT, payment_method TEXT, success INTEGER, revenue REAL, margin REAL, delayed INTEGER, repeated INTEGER, payload TEXT);
        CREATE TABLE IF NOT EXISTS bank_transactions(id TEXT PRIMARY KEY,timestamp TEXT,bank_status TEXT,app_status TEXT,amount_cents INTEGER);
        CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,transaction_id TEXT,amount_cents INTEGER,kind TEXT,timestamp TEXT);
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,timestamp TEXT,action TEXT,detail TEXT);
        CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY,payload TEXT);
        CREATE TABLE IF NOT EXISTS deployments(id TEXT PRIMARY KEY,timestamp TEXT,version TEXT,components TEXT);"""
        )
        if "account_id" not in [
            r[1] for r in self.db.execute("PRAGMA table_info(bank_transactions)")
        ]:
            self.db.execute("ALTER TABLE bank_transactions ADD COLUMN account_id TEXT")
            self.db.execute(
                "UPDATE bank_transactions SET account_id='legacy-unattributed' WHERE account_id IS NULL"
            )
        if "amount_cents" not in [
            r[1] for r in self.db.execute("PRAGMA table_info(bank_transactions)")
        ]:
            self.db.execute(
                "ALTER TABLE bank_transactions RENAME COLUMN amount TO amount_cents"
            )
            self.db.execute("ALTER TABLE ledger RENAME COLUMN amount TO amount_cents")
            self.db.execute(
                "UPDATE bank_transactions SET amount_cents=CAST(ROUND(amount_cents*100) AS INTEGER)"
            )
            self.db.execute(
                "UPDATE ledger SET amount_cents=CAST(ROUND(amount_cents*100) AS INTEGER)"
            )
        if not self.get("seeded"):
            self.reset()
        for row in self.db.execute("SELECT id,payload FROM findings").fetchall():
            f = json.loads(row["payload"])
            if "commits" not in f:
                from github_integration import DEMO_COMMITS, rank_commits

                f["commits"] = rank_commits(DEMO_COMMITS, f["scenario"])
                f["score"] = f["commits"][0]["score"]
                f["commit_sha"] = f["commits"][0]["sha"]
                self.db.execute(
                    "UPDATE findings SET payload=? WHERE id=?", (json.dumps(f), f["id"])
                )
        self.db.commit()

    def get(self, k, default=None):
        with LOCK:
            row = self.db.execute(
                "SELECT value FROM state WHERE key=?", (k,)
            ).fetchone()
            return json.loads(row[0]) if row else default

    def set(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (k, json.dumps(v)))

    def audit(self, a, d):
        self.db.execute(
            "INSERT INTO audit VALUES (?,?,?,?)", (str(uuid.uuid4()), now(), a, d)
        )

    def generate(self, phase, count, start, hours, scenario=None):
        rng = random.Random(42 + sum(map(ord, phase)))
        rows = []
        for i in range(count):
            safari = rng.random() < 0.34
            paypal = rng.random() < 0.63
            browser = "Safari" if safari else "Chrome"
            payment = "PayPal" if paypal else "Card"
            rate = 0.72
            if scenario == "checkout" and safari and paypal:
                rate = 0.36
            success = int(rng.random() < rate)
            amount = round(rng.uniform(64, 100), 2)
            promo = scenario == "promotion" and rng.random() < 0.27
            revenue = amount * (0.55 if promo else 1) * success
            margin = (revenue - amount * 0.64 * success) if promo else revenue * 0.36
            delayed = int(rng.random() < 0.18)
            repeat = int(
                rng.random() < (0.14 if delayed and scenario == "delivery" else 0.42)
            )
            ts = (start + timedelta(hours=hours * i / count)).isoformat()
            payload = {
                "source": "simulator",
                "event_type": "checkout_completed" if success else "payment_failed",
                "session_id": f"{phase}-{i}",
                "browser": browser,
                "payment_method": payment,
                "amount": amount,
                "release": "checkout-v42" if scenario == "checkout" else "checkout-v41",
                "coupons": ["WELCOME20", "SUMMER25"] if promo else [],
                "delivery_days": 7 if delayed else 2,
            }
            rows.append(
                (
                    str(uuid.uuid4()),
                    ts,
                    phase,
                    browser,
                    payment,
                    success,
                    round(revenue, 2),
                    round(margin, 2),
                    delayed,
                    repeat,
                    json.dumps(payload),
                )
            )
        self.db.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)

    def reset(self):
        with LOCK:
            for t in [
                "events",
                "audit",
                "findings",
                "deployments",
                "bank_transactions",
                "ledger",
            ]:
                self.db.execute(f"DELETE FROM {t}")
            current = datetime.now(timezone.utc)
            self.generate("baseline", 30000, current - timedelta(days=31), 720)
            self.generate("live", 6000, current - timedelta(hours=1), 1)
            self.set("seeded", True)
            self.set("scenario", None)
            self.set("status", "healthy")
            self.set("avoided_daily", 0)
            self.audit(
                "Demo reset",
                "30 days of historical synthetic sessions and one hour of healthy traffic generated.",
            )
            self.db.commit()
        return self.dashboard()

    def stats(self, phase, where="", params=()):
        row = self.db.execute(
            "SELECT COUNT(*) n,AVG(success) conversion,SUM(revenue) revenue,AVG(revenue) rps,SUM(margin) margin FROM events WHERE phase=? "
            + where,
            (phase, *params),
        ).fetchone()
        return dict(row)

    def launch(self, scenario, assess=True):
        if scenario not in ["checkout", "promotion", "delivery", "banking"]:
            raise ValueError("Unknown scenario")
        with LOCK:
            if self.get("status") in ("active", "unassessed"):
                raise ValueError(
                    "Resolve the current scenario or reset before launching another"
                )
            self.db.execute("SAVEPOINT assessment")
            try:
                self.db.execute("DELETE FROM events WHERE phase IN ('live','recovery')")
                current = datetime.now(timezone.utc)
                self.generate("live", 6000, current - timedelta(hours=1), 1, scenario)
                if scenario == "banking":
                    self.generate_bank()
                version = {
                    "checkout": "checkout-v42",
                    "promotion": "campaign-stack-v3",
                    "delivery": "delivery-routing-v18",
                    "banking": "payments-adapter-v12",
                }[scenario]
                self.db.execute(
                    "INSERT OR REPLACE INTO deployments VALUES (?,?,?,?)",
                    (
                        str(uuid.uuid4()),
                        (current - timedelta(minutes=67)).isoformat(),
                        version,
                        json.dumps(
                            {
                                "checkout": ["paypal_redirect", "payment_retry"],
                                "promotion": ["discount_combiner"],
                                "delivery": ["carrier_routing"],
                                "banking": ["settlement_status_mapper"],
                            }[scenario]
                        ),
                    ),
                )
                self.set("scenario", scenario)
                self.set("status", "active")
                self.set("started", now())
                finding = self.observe(scenario)
                if assess:
                    from investigator import detect_anomaly

                    decision = detect_anomaly(
                        finding,
                        self.get(
                            "analysis_policy",
                            "Check business outcomes, accounting consistency, traffic and data quality.",
                        ),
                    )
                    finding.update(
                        detection=decision,
                        detection_provider=decision["provider"],
                        reasoning_provider=decision["provider"],
                        classification=decision["classification"],
                        summary=decision["summary"],
                        status=(
                            "active"
                            if decision["detected"] is True
                            else (
                                "healthy"
                                if decision["detected"] is False
                                else "unassessed"
                            )
                        ),
                    )
                else:
                    finding.update(
                        status="unassessed",
                        classification="inconclusive",
                        detection_provider="Awaiting cached Gemini decision",
                    )
                self.set("status", finding["status"])
                self.db.execute(
                    "INSERT OR REPLACE INTO findings VALUES (?,?)",
                    (finding["id"], json.dumps(finding)),
                )
                self.set("current", finding["id"])
                self.audit(
                    "Change introduced",
                    f"{version}: simulated regression injected into customer events.",
                )
                self.audit(
                    "Anomaly window assessed",
                    finding["detection_provider"] + ": " + finding["classification"],
                )
                self.db.execute("RELEASE assessment")
            except Exception:
                self.db.execute("ROLLBACK TO assessment")
                self.db.execute("RELEASE assessment")
                raise
            self.db.commit()
        return self.dashboard()

    def observe(self, scenario):
        """Collect measurements and scenario metadata, without an anomaly verdict."""
        b = self.stats("baseline")
        a = self.stats("live")
        n = a["n"]
        delta = b["conversion"] - a["conversion"]
        z = delta / math.sqrt(
            b["conversion"] * (1 - b["conversion"]) * (1 / b["n"] + 1 / n)
        )
        base = {
            "id": str(uuid.uuid4()),
            "scenario": scenario,
            "status": "active",
            "created_at": now(),
            "sample_size": n,
            "reasoning_provider": "Awaiting Gemini",
            "confidence_label": "Correlation score, not causal probability",
            "owner": "Unassigned",
            "notes": [],
            "baseline": b,
            "actual": a,
            "z_score": round(z, 2),
        }
        if scenario == "checkout":
            seller_checkout_starts_per_day = 120
            exposure = max(0, delta) * seller_checkout_starts_per_day * 82
            segments = []
            for browser, payment in [
                ("Safari", "PayPal"),
                ("Chrome", "PayPal"),
                ("Safari", "Card"),
                ("Chrome", "Card"),
            ]:
                sb = self.stats(
                    "baseline", "AND browser=? AND payment_method=?", (browser, payment)
                )
                sa = self.stats(
                    "live", "AND browser=? AND payment_method=?", (browser, payment)
                )
                segments.append(
                    {
                        "name": browser + " / " + payment,
                        "baseline": sb["conversion"],
                        "actual": sa["conversion"],
                        "sessions": sa["n"],
                    }
                )
            score = 0.3 * math.exp(-7 / 60) + 0.3 + 0.2 + 0.1 + 0.1
            base.update(
                title="Checkout conversion regression",
                severity="critical",
                metric="Checkout conversion",
                unit="day",
                exposure=round(exposure),
                score=round(score, 2),
                segment="Safari + PayPal",
                cause="checkout-v42",
                action="Roll back checkout-v42",
                relative_change=round(delta / b["conversion"] * 100, 1),
                segments=segments,
                summary="The conversion decline is concentrated in Safari sessions using PayPal. The affected release changed the payment redirect handler seven minutes before the simulated decline. Unaffected segments remain close to baseline. This supports a release regression hypothesis, but does not prove causation.",
                formula=f"120 seller checkout starts/day × ({b['conversion']:.4f} − {a['conversion']:.4f}) × $82 assumed order value",
                evidence=[
                    {
                        "label": "Segment isolation",
                        "value": f"{segments[0]['baseline'] * 100:.1f}% → {segments[0]['actual'] * 100:.1f}% conversion",
                        "detail": "Safari / PayPal sessions, measured from persisted events",
                    },
                    {
                        "label": "Statistical signal",
                        "value": f"{z:.1f} standard errors below baseline",
                        "detail": "Two-proportion comparison using 30,000 baseline and 6,000 current sessions",
                    },
                    {
                        "label": "Change correlation",
                        "value": "7 minute simulated lead time",
                        "detail": "Release modified paypal_redirect and payment_retry",
                    },
                ],
            )
        elif scenario == "promotion":
            leaks = self.db.execute(
                "SELECT COUNT(*) n,SUM(-margin) loss FROM events WHERE phase='live' AND margin<0"
            ).fetchone()
            exposure = (leaks["loss"] or 0) / n * 120 * 7
            base.update(
                title="Stacked discounts erase order margin",
                severity="high",
                metric="Contribution margin",
                unit="week",
                exposure=round(exposure),
                score=0.89,
                segment="WELCOME20 + SUMMER25",
                cause="campaign-stack-v3",
                action="Disable coupon stacking",
                relative_change=round(
                    (b["margin"] / b["revenue"] - a["margin"] / a["revenue"]) * 100, 1
                ),
                segments=[],
                summary=f"{leaks['n']:,} successful orders combine WELCOME20 and SUMMER25. The combined discount leaves less revenue than the assumed product cost. Traffic and uptime remain healthy while contribution margin deteriorates.",
                formula=f"${leaks['loss'] / n:,.2f} negative margin per sampled checkout × 120 seller checkouts/day × 7",
                evidence=[
                    {
                        "label": "Unprofitable orders",
                        "value": f"{leaks['n']:,} orders",
                        "detail": "Orders with negative contribution margin in the last simulated hour",
                    },
                    {
                        "label": "Discount overlap",
                        "value": "45% combined discount",
                        "detail": "20% + 25% additive stacking against 64% assumed product cost",
                    },
                    {
                        "label": "Margin exposure",
                        "value": f"${leaks['loss']:,.2f} in the demo cohort",
                        "detail": "Observed cohort margin loss. Seller projection scales to 120 checkout starts/day.",
                    },
                ],
            )
        elif scenario == "delivery":
            cohorts = []
            for delayed in [0, 1]:
                row = self.db.execute(
                    "SELECT COUNT(*) n,AVG(repeated) rate FROM events WHERE phase='live' AND delayed=?",
                    (delayed,),
                ).fetchone()
                cohorts.append(dict(row))
            delta = cohorts[0]["rate"] - cohorts[1]["rate"]
            monthly_delayed_customers = (
                120 * b["conversion"] * 30 * (cohorts[1]["n"] / n)
            )
            exposure = max(0, delta) * monthly_delayed_customers * 82 * 12
            base.update(
                title="Delivery delays weaken repeat purchases",
                severity="high",
                metric="30-day repeat purchase",
                unit="year",
                exposure=round(exposure),
                score=0.84,
                segment="Delivery delayed >5 days",
                cause="delivery-routing-v18",
                action="Restore previous carrier routing",
                relative_change=round(delta * 100, 1),
                segments=[],
                summary="The simulated mature customer cohort shows lower repeat purchase rates after deliveries delayed more than five days. This is an association. Customer mix and order characteristics may also explain the gap. The annual scenario scales the observed delayed-cohort share to 120 seller checkout starts/day and assumes the pattern persists.",
                formula=f"{monthly_delayed_customers:.1f} projected delayed customers/month × ({cohorts[0]['rate']:.4f} − {cohorts[1]['rate']:.4f}) × $82 × 12",
                evidence=[
                    {
                        "label": "On-time cohort",
                        "value": f"{cohorts[0]['rate'] * 100:.1f}% repurchase",
                        "detail": f"{cohorts[0]['n']:,} mature synthetic customer outcomes",
                    },
                    {
                        "label": "Delayed cohort",
                        "value": f"{cohorts[1]['rate'] * 100:.1f}% repurchase",
                        "detail": f"{cohorts[1]['n']:,} mature synthetic customer outcomes",
                    },
                    {
                        "label": "Projection assumption",
                        "value": "Seller volume scaled monthly",
                        "detail": "Annual scenario estimate, not realized loss",
                    },
                ],
            )
        else:
            mismatch = self.db.execute(
                "SELECT COUNT(*) n,SUM(amount_cents) exposure FROM bank_transactions WHERE bank_status!='settled' AND app_status='success'"
            ).fetchone()
            base.update(
                title="Failed payments posted as settled credits",
                severity="critical",
                metric="Settlement reconciliation",
                unit="unbacked",
                exposure=mismatch["exposure"] / 100,
                score=0,
                segment="Failed / pending bank transfers",
                cause="payments-adapter-v12",
                action="Reconcile and reverse unbacked credits",
                relative_change=0,
                segments=[],
                sample_size=2000,
                summary=f"{mismatch['n']} transactions are marked successful in the app although the simulated bank status is failed or pending. The ledger contains credits with no settlement evidence. This is a reconciliation mismatch, not proof that cash has arrived. Review the status mapper and stop recognizing unsettled credits.",
                formula="Sum of credited amounts where app_status = success and bank_status != settled",
                evidence=[
                    {
                        "label": "Status mismatches",
                        "value": str(mismatch["n"]) + " transactions",
                        "detail": "Application success compared with authoritative simulated settlement status",
                    },
                    {
                        "label": "Unbacked ledger credits",
                        "value": "$" + format(mismatch["exposure"] / 100, ",.2f"),
                        "detail": "Observed accounting discrepancy, not an annual revenue projection",
                    },
                    {
                        "label": "Failure handling",
                        "value": "failed and pending mapped to success",
                        "detail": "Status mapper uses a fallback success branch instead of requiring settlement",
                    },
                ],
            )
        from github_integration import DEMO_COMMITS, rank_commits

        onset = datetime.now(timezone.utc) - timedelta(hours=1)
        fixture_onset = datetime.fromisoformat("2026-10-10T14:09:00+00:00")
        commits = [
            {
                **c,
                "timestamp": (
                    datetime.fromisoformat(c["timestamp"]) + (onset - fixture_onset)
                ).isoformat(),
            }
            for c in DEMO_COMMITS
        ]
        base["heuristic_commits"] = rank_commits(commits, scenario, onset.isoformat())
        base["commits"] = [
            {**c, "deployment_eligible": True}
            for c in sorted(commits, key=lambda x: x["sha"])
        ]
        base["score"] = 0
        base["commit_sha"] = "Awaiting AI"
        base["deployment_mapping"] = {
            "kind": "synthetic fixture",
            "release_window": onset.isoformat(),
            "candidate_shas": [c["sha"] for c in commits],
        }
        base["observations"] = [
            {
                "id": "e" + str(i + 1),
                "label": e["label"],
                "value": e["value"],
                "detail": e["detail"],
            }
            for i, e in enumerate(base["evidence"])
        ]
        if scenario == "banking":
            base["observations"] = base["observations"][:2]
            base["bank_accounts"] = self.bank_accounts()
        base["timeline"] = [
            {
                "time": (onset - timedelta(minutes=7)).strftime("%H:%M"),
                "title": "Business change shipped",
                "detail": base["cause"],
            },
            {
                "time": onset.strftime("%H:%M"),
                "title": "Customer outcome diverged",
                "detail": base["segment"],
            },
            {
                "time": (onset + timedelta(minutes=2)).strftime("%H:%M"),
                "title": "Measurement window collected",
                "detail": base["metric"],
            },
            {
                "time": (onset + timedelta(minutes=5)).strftime("%H:%M"),
                "title": "Investigation ready",
                "detail": "Measurements and candidate diffs available for Gemini",
            },
        ]
        base["classification"] = "inconclusive"
        base["classification_basis"] = (
            "Gemini assesses the supplied window; numerical measurements do not determine the verdict."
        )
        base.pop("action", None)
        base["title"] = {
            "checkout": "Checkout completion",
            "promotion": "Order contribution margin",
            "delivery": "Customer repurchase",
            "banking": "Settlement consistency",
        }[scenario]
        return base

    def finding(self, finding_id=None):
        with LOCK:
            row = self.db.execute(
                "SELECT payload FROM findings WHERE id=?",
                (finding_id or self.get("current"),),
            ).fetchone()
            if not row:
                return None
            f = json.loads(row[0])
            f.setdefault(
                "classification",
                (
                    "operational_incident"
                    if f.get("scenario") == "delivery"
                    else "business_regression"
                ),
            )
            return format_finding(f)

    def action(self, action, finding_id=None):
        with LOCK:
            f = self.finding(finding_id)
            if not f:
                raise ValueError("No incident to act on")
            if action in ("resolve", "ignore", "not_issue", "reopen"):
                f["status"] = {
                    "resolve": "resolved",
                    "ignore": "ignored",
                    "not_issue": "not_issue",
                    "reopen": "active",
                }[action]
                f["reviewed_at"] = now()
                f["review_note"] = (
                    "Manual review. Source measurements and ledger entries were not changed."
                )
                if f["id"] == self.get("current"):
                    self.set("status", f["status"])
                self.audit("Issue reviewed", action + ": " + f["title"])
            elif action == "assign":
                f["owner"] = "You"
                self.audit(
                    "Incident assigned",
                    "Incident assigned to the current demo operator.",
                )
            else:
                raise ValueError("Unknown action")
            self.db.execute(
                "UPDATE findings SET payload=? WHERE id=?", (json.dumps(f), f["id"])
            )
            self.db.commit()
        return self.dashboard()

    def dashboard(self):
        with LOCK:
            phase = "recovery" if self.get("status") == "recovered" else "live"
            b = self.stats("baseline")
            a = self.stats(phase)
            f = self.finding()
            series = []
            for i in range(24):
                chart_phase = "baseline" if i < 12 else phase
                start = (i if i < 12 else i - 12) * 500
                row = self.db.execute(
                    "SELECT AVG(success) rate,SUM(revenue) revenue FROM (SELECT success,revenue FROM events WHERE phase=? ORDER BY timestamp LIMIT 500 OFFSET ?)",
                    (chart_phase, start),
                ).fetchone()
                series.append(
                    {
                        "time": f"{13 + i // 12:02}:{(i % 12) * 5:02}",
                        "actual": round((row["rate"] or 0) * 100, 1),
                        "expected": round(b["conversion"] * 100, 1),
                        "revenue": round(row["revenue"] or 0),
                    }
                )
            history = [
                format_finding(json.loads(r[0]))
                for r in self.db.execute(
                    "SELECT payload FROM findings ORDER BY rowid DESC"
                )
            ]
            return {
                "status": self.get("status"),
                "scenario": self.get("scenario"),
                "baseline": b,
                "metrics": a,
                "finding": f,
                "history": history,
                "series": series,
                "event_count": self.db.execute(
                    "SELECT COUNT(*) FROM events"
                ).fetchone()[0],
                "avoided_daily": self.get("avoided_daily", 0),
                "audit": [
                    dict(r)
                    for r in self.db.execute(
                        "SELECT timestamp,action,detail FROM audit ORDER BY rowid DESC LIMIT 30"
                    )
                ],
                "deployments": [
                    dict(r)
                    for r in self.db.execute(
                        "SELECT * FROM deployments ORDER BY timestamp DESC"
                    )
                ],
                "banking": self.bank_summary(),
                "seller": {
                    "name": "Luma Goods",
                    "platform": "Shopify-shaped demo events",
                    "checkout_starts_per_day": 120,
                    "aov": 82,
                },
                "mode": "Synthetic demo",
                "cloud": {
                    "bigquery": False,
                    "gemini_configured": __import__("cloud_identity").configured(),
                },
                "deployment": {
                    "environment": "Cloud Run" if os.getenv("K_SERVICE") else "Local",
                    "durable": bool(os.getenv("IMPACTGUARD_STORAGE_BUCKET")),
                },
                "updated_at": now(),
            }

    def generate_bank(self):
        self.db.execute("DELETE FROM bank_transactions")
        self.db.execute("DELETE FROM ledger")
        rng = random.Random(73)
        for i in range(2000):
            txid = f"tx_{i:05d}"
            status = "settled" if i % 10 else ("failed" if i % 20 else "pending")
            amount = rng.randint(
                2000, 45000
            )  # integer cents, never binary floating point for postings
            app_status = (
                "success"  # injected mapper bug: all callbacks treated as successful
            )
            self.db.execute(
                "INSERT INTO bank_transactions VALUES (?,?,?,?,?,?)",
                (
                    txid,
                    now(),
                    status,
                    app_status,
                    amount,
                    (
                        f"acct_sim_{(i//10)%5:03d}"
                        if i % 10 == 0
                        else f"acct_sim_{100+i%400:03d}"
                    ),
                ),
            )
            self.db.execute(
                "INSERT INTO ledger VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), txid, amount, "credit", now()),
            )

    def bank_accounts(self):
        grouped = {}
        for row in self.reconciliation_rows():
            account = row.get("account_id") or "legacy-unattributed"
            item = grouped.setdefault(
                account,
                {
                    "account_id": account,
                    "mismatch_count": 0,
                    "failed_count": 0,
                    "pending_count": 0,
                    "unbacked_cents": 0,
                    "transaction_ids": [],
                },
            )
            item["mismatch_count"] += 1
            item["failed_count"] += int(row["bank_status"] == "failed")
            item["pending_count"] += int(row["bank_status"] == "pending")
            item["unbacked_cents"] += max(
                0, row["net_credit_cents"] - row["expected_credit_cents"]
            )
            if len(item["transaction_ids"]) < 6:
                item["transaction_ids"].append(row["id"])
        return sorted(
            grouped.values(), key=lambda x: (-x["mismatch_count"], x["account_id"])
        )[:20]

    def investigate_finding(self, finding_id=None):
        from investigator import investigate

        f = self.finding(finding_id)
        if not f:
            raise ValueError("Collect a window first")
        result = investigate(
            f,
            self.get(
                "analysis_policy",
                "Compare business evidence against all supplied candidate diffs.",
            ),
        )
        f["investigation"] = result
        if result.get("attribution_status") == "validated_reference":
            f["commit_sha"] = result["suspect_commit_sha"]
        self.db.execute(
            "UPDATE findings SET payload=? WHERE id=?", (json.dumps(f), f["id"])
        )
        self.db.commit()
        return result

    def reconciliation_rows(self):
        rows = self.db.execute(
            "SELECT t.*,COALESCE(SUM(l.amount_cents),0) net_credit_cents FROM bank_transactions t LEFT JOIN ledger l ON l.transaction_id=t.id GROUP BY t.id"
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["expected_credit_cents"] = (
                item["amount_cents"] if item["bank_status"] == "settled" else 0
            )
            expected_status = (
                "success" if item["bank_status"] == "settled" else item["bank_status"]
            )
            if (
                item["net_credit_cents"] != item["expected_credit_cents"]
                or item["app_status"] != expected_status
            ):
                result.append(item)
        return result

    def bank_summary(self):
        discrepancies = self.reconciliation_rows()
        total = self.db.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0]
        examples = (
            discrepancies[:12]
            if discrepancies
            else [
                dict(r)
                for r in self.db.execute(
                    "SELECT * FROM bank_transactions WHERE bank_status!='settled' LIMIT 12"
                )
            ]
        )
        return {
            "total": total,
            "mismatches": len(discrepancies),
            "exposure": sum(
                max(0, r["net_credit_cents"] - r["expected_credit_cents"])
                for r in discrepancies
            )
            / 100,
            "missing_credits": sum(
                max(0, r["expected_credit_cents"] - r["net_credit_cents"])
                for r in discrepancies
            )
            / 100,
            "transactions": [
                {**r, "amount": r["amount_cents"] / 100} for r in examples
            ],
            "accounts": self.bank_accounts(),
            "account_reviews": (self.finding() or {})
            .get("detection", {})
            .get("accounts_review", []),
            "reversals": self.db.execute(
                "SELECT COUNT(*) FROM ledger WHERE kind='reversal'"
            ).fetchone()[0],
        }

    def ingest(self, event):
        required = ["timestamp", "source", "event_type", "session_id"]
        if any(not event.get(k) for k in required):
            raise ValueError("Required fields: " + ", ".join(required))
        if any(not isinstance(event[k], str) for k in required):
            raise ValueError("Required event fields must be strings")
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        if not timestamp.tzinfo:
            raise ValueError("Timestamp must include a timezone")
        eid = event.get("event_id") or str(uuid.uuid4())
        success = int(event["event_type"] in ["order_created", "checkout_completed"])
        amount = float(event.get("amount", 0))
        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Amount must be finite and nonnegative")
        with LOCK:
            self.db.execute(
                "INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    eid,
                    event["timestamp"],
                    "external",
                    event.get("browser", "Unknown"),
                    event.get("payment_method", "Unknown"),
                    success,
                    amount * success,
                    amount * success * 0.36,
                    0,
                    0,
                    __import__("security").redact(json.dumps(event)),
                ),
            )
            self.db.commit()
        return {
            "event_id": eid,
            "accepted": True,
            "scope": "external events stored separately from demo analytics",
        }
