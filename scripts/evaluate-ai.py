#!/usr/bin/env python3
"""Reproducible synthetic benchmark. Executes trusted fixture functions, never model drafts."""

import argparse, hashlib, json, random, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from investigator import investigate, detect_anomaly
from github_integration import rank_commits

# Each controlled bug violates a business contract; the good version passes the same guard.
SPECS = [
    (
        "banking",
        "settlement eligibility",
        "status",
        'status == "settled"',
        'status != "cancelled"',
        "failed",
        False,
    ),
    (
        "banking",
        "pending settlement",
        "status",
        'status == "settled"',
        'status in ("settled", "pending")',
        "pending",
        False,
    ),
    ("banking", "reversal sign", "amount", "-abs(amount)", "abs(amount)", 8300, -8300),
    ("banking", "retry idempotency", "seen", "0 if seen else 8300", "8300", True, 0),
    (
        "banking",
        "duplicate callbacks",
        "count",
        "8300 if count == 1 else 0",
        "8300",
        2,
        0,
    ),
    (
        "banking",
        "minor currency units",
        "amount",
        "round(amount * 100)",
        "round(amount * 1000)",
        82,
        8200,
    ),
    ("banking", "net settlement", "gross", "gross - 200", "gross + 200", 8300, 8100),
    (
        "promotion",
        "discount composition",
        "price",
        "price * .8 * .75",
        "price * (1-.2-.25)",
        100,
        60.0,
    ),
    (
        "promotion",
        "duplicate promotion",
        "price",
        "price * .8",
        "price * .8 * .8",
        100,
        80.0,
    ),
    (
        "promotion",
        "discount cap",
        "discount",
        "min(discount, 30)",
        "max(discount, 30)",
        45,
        30,
    ),
    (
        "promotion",
        "tax calculation",
        "price",
        "price * .8 * 1.1",
        "price * .8 + price * .1",
        100,
        88.0,
    ),
    (
        "checkout",
        "shipping eligibility",
        "subtotal",
        "subtotal >= 50",
        "subtotal <= 50",
        30,
        False,
    ),
    ("banking", "refund direction", "amount", "-amount", "amount", 1200, -1200),
    (
        "banking",
        "refund percentage",
        "amount",
        "round(amount * .25)",
        "round(amount * 25)",
        8000,
        2000,
    ),
    (
        "banking",
        "cashback settlement",
        "status",
        'status == "settled"',
        'status != "failed"',
        "pending",
        False,
    ),
    ("delivery", "delivery promise", "days", "days <= 5", "days <= 15", 10, False),
    ("checkout", "missing payment token", "token", "bool(token)", "True", "", False),
    (
        "checkout",
        "redirect token source",
        "session_token",
        "session_token",
        '""',
        "valid-token",
        "valid-token",
    ),
    (
        "banking",
        "callback business status",
        "status",
        'status == "settled"',
        "True",
        "failed",
        False,
    ),
    ("banking", "timeout handling", "timed_out", "not timed_out", "True", True, False),
    ("banking", "payout fees", "gross", "gross - 300", "gross", 9000, 8700),
    ("promotion", "contribution margin", "revenue", "revenue - 64", "revenue", 55, -9),
    (
        "banking",
        "rounding to minor units",
        "amount",
        "round(amount * 100)",
        "int(amount * 100)",
        10.129,
        1013,
    ),
    (
        "delivery",
        "carrier routing",
        "premium",
        '"express" if premium else "economy"',
        '"economy"',
        True,
        "express",
    ),
    (
        "delivery",
        "mature retention cohorts",
        "days",
        "days >= 30",
        "days <= 30",
        12,
        False,
    ),
]


def run_guard(argument, expression, value):
    namespace = {}
    # Fixture strings above are authored here. No model or repository code is executed.
    exec(
        "def evaluate(" + argument + "):\n    return " + expression,
        {
            "__builtins__": {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "bool": bool,
                "int": int,
            }
        },
        namespace,
    )
    return namespace["evaluate"](value)


def patch(expression, argument, old="None"):
    return (
        "@@ -40,2 +40,2 @@\n def evaluate("
        + argument
        + "):\n-    return "
        + old
        + "\n+    return "
        + expression
    )


def dataset():
    cases = []
    for i, (scenario, metric, arg, good, bad, value, expected) in enumerate(SPECS):
        actual = run_guard(arg, bad, value)
        fixed = run_guard(arg, good, value)
        assert fixed == expected and actual != expected, (i, actual, fixed, expected)
        candidates = []
        truth = None
        target = random.Random(9107 + i).randrange(5)
        logging_decoy = (target + 1) % 5
        good_decoy = (target + 2) % 5
        for j in range(5):
            sha = hashlib.sha256(f"eval-v1-{i}-{j}".encode()).hexdigest()[:40]
            file = f'src/{scenario}/module_{hashlib.sha256(f"path-{i}-{j}".encode()).hexdigest()[:6]}.py'
            start_line = 40 + random.Random(i * 10 + j + 700).randrange(150)
            if j == target:
                diff = patch(bad, arg, good)
                truth = {"sha": sha, "file": file, "line": start_line + 1}
            elif j == logging_decoy:
                # A realistic logging-only decoy with strong domain terms.
                terms = {
                    "checkout": "checkout paypal redirect token payment safari",
                    "banking": "bank settlement failed pending success credit status callback payment ledger",
                    "promotion": "coupon discount stack campaign margin promotion price",
                    "delivery": "delivery carrier routing delayed repeat retention cohort",
                }[scenario]
                diff = (
                    "@@ -40,2 +40,3 @@\n def record_metric(event):\n-    return event\n+    # "
                    + terms
                    + "\n+    return event"
                )
            elif j == good_decoy:
                diff = patch("(" + good + ")", arg, good)
            elif j == 3:
                diff = "@@ -40,2 +40,2 @@\n def label(value):\n-    return str(value)\n+    return str(value).strip()"
            else:
                diff = "@@ -40,2 +40,2 @@\n def cache_ttl():\n-    return 60\n+    return 120"
            diff = diff.replace("-40,", "-" + str(start_line) + ",").replace(
                "+40,", "+" + str(start_line) + ","
            )
            candidates.append(
                {
                    "sha": sha,
                    "repo": "evaluation/fixture",
                    "message": "Update business service",
                    "timestamp": "2026-10-10T14:02:00+00:00",
                    "deployment_eligible": True,
                    "files": [
                        {
                            "filename": file,
                            "patch": diff,
                            "additions": 2,
                            "deletions": 1,
                        }
                    ],
                }
            )
        random.Random(1701 + i).shuffle(candidates)
        observation = {
            "metric": metric,
            "scenario": scenario,
            "deployment_mapping": {
                "kind": "synthetic release bundle",
                "candidate_shas": [c["sha"] for c in candidates],
            },
            "observations": [
                {
                    "id": "e1",
                    "expected_outcome": expected,
                    "observed_outcome": actual,
                    "sample_size": 1200,
                    "input_condition": {arg: value},
                }
            ],
            "commits": candidates,
            "segments": [],
        }
        cases.append(
            {
                "id": f"bug-{i+1:02d}",
                "observation": observation,
                "ground_truth": truth,
                "guard_verified": True,
            }
        )
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--output-dir", default="output/evaluation")
    args = ap.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    cases = dataset()
    (out / "planted-bugs.json").write_text(json.dumps(cases, indent=2))
    if not args.live:
        print("25 controlled bug guards verified; dataset saved. No model call.")
        return
    records = []
    old = out / "raw-results.json"
    if old.exists():
        records = json.loads(old.read_text())
    done = {r["id"] for r in records}
    for case in cases[: args.limit]:
        if case["id"] in done:
            continue
        observation = case["observation"]
        start = time.monotonic()
        record = {"id": case["id"], "ground_truth": case["ground_truth"]}
        heuristic = rank_commits(
            observation["commits"], observation["scenario"], "2026-10-10T14:09:00+00:00"
        )[0]
        record["heuristic_sha"] = heuristic["sha"]
        try:
            decision = detect_anomaly(observation)
            result = investigate(observation)
            record.update(
                detection=decision,
                result=result,
                llm_top1=result.get("suspect_commit_sha")
                == case["ground_truth"]["sha"],
                exact_reference=all(
                    result.get(k) == case["ground_truth"][v]
                    for k, v in [
                        ("suspect_commit_sha", "sha"),
                        ("file", "file"),
                        ("line", "line"),
                    ]
                ),
            )
        except ValueError as e:
            record.update(error=str(e), llm_top1=False, exact_reference=False)
        record["heuristic_top1"] = heuristic["sha"] == case["ground_truth"]["sha"]
        record["seconds"] = round(time.monotonic() - start, 2)
        records.append(record)
        old.write_text(json.dumps(records, indent=2))
        print(
            record["id"],
            "Gemini:",
            record["llm_top1"],
            "heuristic:",
            record["heuristic_top1"],
            flush=True,
        )
    n = len(records)
    tokens = sum(
        (r.get(kind, {}).get("usage", {}).get("total_tokens") or 0)
        for r in records
        for kind in ("result", "detection")
    )
    summary = {
        "dataset_version": "planted-v2",
        "model": __import__("os").getenv("GEMINI_MODEL"),
        "cases": n,
        "llm_top1": sum(r["llm_top1"] for r in records),
        "heuristic_top1": sum(r["heuristic_top1"] for r in records),
        "validated_exact_reference": sum(r["exact_reference"] for r in records),
        "errors": sum("error" in r for r in records),
        "total_tokens": tokens,
        "limitation": "Synthetic, controlled business contracts and a keyword-heavy logging decoy per case. Not production performance. No training or tuning on returned answers; all attempts, abstentions, invalid citations and errors count in the denominator.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
