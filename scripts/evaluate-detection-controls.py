"""Small healthy and non-regression controls; no preset decisions sent to Gemini."""

import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from investigator import detect_anomaly

cases = [
    (
        "healthy-stable",
        "healthy",
        False,
        {
            "baseline_sessions": 10000,
            "recent_sessions": 10000,
            "baseline_completion_rate": 0.60,
            "recent_completion_rate": 0.601,
            "collection_complete": True,
        },
    ),
    (
        "healthy-volume",
        "healthy",
        False,
        {
            "baseline_sessions": 10000,
            "recent_sessions": 15000,
            "baseline_completion_rate": 0.60,
            "recent_completion_rate": 0.60,
            "campaign": "planned advertising campaign",
            "collection_complete": True,
        },
    ),
    (
        "healthy-ledger",
        "healthy",
        False,
        {
            "application_success_count": 2000,
            "bank_settled_count": 2000,
            "unbacked_credit_cents": 0,
            "collection_complete": True,
        },
    ),
    (
        "traffic-spike",
        "traffic_anomaly",
        True,
        {
            "baseline_sessions": 10000,
            "recent_sessions": 100000,
            "baseline_completion_rate": 0.60,
            "recent_completion_rate": 0.60,
            "campaign": "none",
            "collection_complete": True,
        },
    ),
    (
        "security-requests",
        "security_signal",
        True,
        {
            "baseline_blocked_requests": 5,
            "recent_blocked_requests": 5000,
            "blocked_reason": "credential stuffing signatures",
            "confirmed_compromise": False,
            "checkout_rate_unchanged": True,
        },
    ),
    (
        "missing-events",
        "data_quality",
        True,
        {
            "baseline_sessions": 10000,
            "recent_sessions": 10000,
            "baseline_purchase_events": 6000,
            "recent_purchase_events": 20,
            "settled_order_records": 6000,
            "purchase_event_collection_gap": True,
        },
    ),
]
rows = []
for name, expected, positive, obs in cases:
    r = detect_anomaly(
        {
            "metric": name,
            "observations": [{"id": "e1", **obs}],
            "commits": [],
            "deployment_mapping": None,
        }
    )
    rows.append(
        {
            "case": name,
            "expected_classification": expected,
            "expected_detected": positive,
            "actual": r,
            "correct": r["classification"] == expected and r["detected"] == positive,
        }
    )
    print(name, r["classification"], rows[-1]["correct"], flush=True)
out = Path("output/evaluation/detection-controls.json")
out.write_text(
    json.dumps(
        {
            "cases": len(rows),
            "correct": sum(r["correct"] for r in rows),
            "limitation": "Six hand-authored controls, not production false-positive measurement. A planned campaign is included as healthy; alternative classifications can be reasonable.",
            "results": rows,
        },
        indent=2,
    )
)
