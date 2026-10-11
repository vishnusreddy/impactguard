"""Project connections; credentials are read from explicit local environment only."""

import os, re, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from security import redact


def state(engine):
    repos = engine.get("project_repos", [])
    snapshots = engine.get("integration_snapshots", {})
    return {
        "project": "Luma Goods",
        "repos": repos,
        "repo": ", ".join(r["repo"] for r in repos),
        "commits": [c for r in repos for c in r["commits"]],
        "connected": bool(repos),
        "snapshots": snapshots,
        "findings": engine.get("source_findings", []),
        "config": engine.get("integration_config", {}),
        "credentials": {
            "shopify": bool(os.getenv("IMPACTGUARD_SHOPIFY_TOKEN")),
            "analytics": bool(os.getenv("IMPACTGUARD_GA_CREDENTIALS")),
            "vertex": bool(
                os.getenv("IMPACTGUARD_VERTEX_PROJECT")
                and os.getenv("IMPACTGUARD_VERTEX_CREDENTIALS")
                and os.getenv("GEMINI_MODEL")
            ),
        },
        "policy": engine.get(
            "analysis_policy",
            "Check checkout completion, payment settlement, discount margin, traffic changes, and data quality. Separate security signals and traffic anomalies from code regressions.",
        ),
    }


def connect(engine, repo):
    from github_integration import normalize_repo, fetch_commits

    repo = normalize_repo(repo)
    commits = fetch_commits(repo)
    repos = engine.get("project_repos", [])
    repos = [r for r in repos if r["repo"] != repo] + [
        {
            "repo": repo,
            "commits": commits,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    if len(repos) > 10:
        raise ValueError("A local project supports up to 10 repositories")
    engine.set("project_repos", repos)
    engine.audit("Codebase connected", repo + ": read-only, redacted commit import")
    engine.db.commit()
    return state(engine)


def configure(engine, body):
    store = body.get("shopify_store", "").strip()
    prop = body.get("ga_property", "").strip()
    if store and not re.fullmatch(r"[a-zA-Z0-9-]+\.myshopify\.com", store):
        raise ValueError("Use the store.myshopify.com domain")
    if prop and not prop.isdigit():
        raise ValueError("GA4 property ID must contain digits")
    policy = body.get("policy", state(engine)["policy"])
    if not isinstance(policy, str) or len(policy) > 1500:
        raise ValueError("Analysis instructions must be at most 1,500 characters")
    engine.set("integration_config", {"shopify_store": store, "ga_property": prop})
    engine.set("analysis_policy", redact(policy))
    engine.db.commit()
    return state(engine)


def sample(source, kind="checkout"):
    if kind not in ("checkout", "traffic", "security", "data_quality"):
        raise ValueError("Unsupported sample scenario")
    days = []
    for i in range(14):
        affected = i >= 11
        days.append(
            {
                "date": (datetime.now(timezone.utc) - timedelta(days=13 - i))
                .date()
                .isoformat(),
                "sessions": (
                    5200
                    if affected and kind in ("traffic", "security")
                    else 1200 + i * 17
                ),
                "orders": (
                    0
                    if affected and kind == "data_quality"
                    else 48 if affected and kind == "checkout" else 86
                ),
                "revenue": (
                    0
                    if affected and kind == "data_quality"
                    else 48 if affected and kind == "checkout" else 86
                )
                * 82,
                "currency": "USD",
                "failed_payments": 12 if affected and kind == "checkout" else 2,
                "blocked_requests": 4500 if affected and kind == "security" else 0,
                "collection_gap": bool(affected and kind == "data_quality"),
            }
        )
    return {
        "source": source,
        "scenario": kind,
        "mode": "synthetic",
        "rows": days,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "disclosure": "Generated sample data. No account was accessed.",
    }


def shopify(config):
    token = os.getenv("IMPACTGUARD_SHOPIFY_TOKEN")
    store = config.get("shopify_store")
    if not token or not store:
        raise ValueError(
            "Configure the store domain and IMPACTGUARD_SHOPIFY_TOKEN locally"
        )
    query = (
        'query($cursor:String){orders(first:100,after:$cursor,sortKey:CREATED_AT,reverse:true,query:"created_at:>='
        + (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
        + '"){nodes{id createdAt displayFinancialStatus totalPriceSet{shopMoney{amount currencyCode}}} pageInfo{hasNextPage endCursor}}}'
    )
    rows = []
    cursor = None
    for page in range(5):
        req = urllib.request.Request(
            "https://" + store + "/admin/api/2026-10/graphql.json",
            data=json.dumps({"query": query, "variables": {"cursor": cursor}}).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": token,
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        if data.get("errors"):
            raise ValueError(
                "Shopify rejected the query. Check read_orders permissions"
            )
        orders = data["data"]["orders"]
        rows.extend(
            {
                "date": v["createdAt"][:10],
                "status": v["displayFinancialStatus"],
                "amount": v["totalPriceSet"]["shopMoney"]["amount"],
                "currency": v["totalPriceSet"]["shopMoney"]["currencyCode"],
            }
            for v in orders["nodes"]
        )
        if not orders["pageInfo"]["hasNextPage"]:
            break
        cursor = orders["pageInfo"]["endCursor"]
    return {
        "source": "shopify",
        "mode": "live",
        "rows": rows,
        "truncated": bool(orders["pageInfo"]["hasNextPage"]),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def analytics(config):
    path = os.getenv("IMPACTGUARD_GA_CREDENTIALS")
    prop = config.get("ga_property")
    if not path or not prop:
        raise ValueError(
            "Configure a GA4 property and dedicated IMPACTGUARD_GA_CREDENTIALS file"
        )
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession

    credentials = service_account.Credentials.from_service_account_file(
        path, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    response = AuthorizedSession(credentials).post(
        "https://analyticsdata.googleapis.com/v1beta/properties/" + prop + ":runReport",
        json={
            "dateRanges": [{"startDate": "14daysAgo", "endDate": "yesterday"}],
            "dimensions": [{"name": "date"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "ecommercePurchases"},
                {"name": "purchaseRevenue"},
            ],
            "limit": 100,
        },
        timeout=20,
    )
    if not response.ok:
        raise ValueError(
            "GA4 rejected the report. Check property access and API enablement"
        )
    data = response.json()
    rows = [
        {
            "date": v["dimensionValues"][0]["value"],
            "sessions": float(v["metricValues"][0]["value"]),
            "orders": float(v["metricValues"][1]["value"]),
            "revenue": float(v["metricValues"][2]["value"]),
        }
        for v in data.get("rows", [])
    ]
    return {
        "source": "analytics",
        "mode": "live",
        "rows": rows,
        "currency": data.get("metadata", {}).get("currencyCode"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def collect(engine, body):
    source = body.get("source")
    if source not in ("shopify", "analytics"):
        raise ValueError("Unsupported integration")
    try:
        snapshot = (
            sample(source, body.get("scenario", "checkout"))
            if body.get("sample") is True
            else (shopify if source == "shopify" else analytics)(
                engine.get("integration_config", {})
            )
        )
    except (urllib.error.URLError, KeyError):
        raise ValueError(
            "Provider request failed. Verify configuration and permissions"
        )
    snapshots = engine.get("integration_snapshots", {})
    snapshots[source] = snapshot
    engine.set("integration_snapshots", snapshots)
    engine.audit("Data collected", source + ": " + snapshot["mode"])
    engine.db.commit()
    return state(engine)


def analyze(engine, body):
    """Analyze aggregated source windows; no raw customers or arbitrary code payloads."""
    source = body.get("source")
    snapshot = engine.get("integration_snapshots", {}).get(source)
    if not snapshot:
        raise ValueError("Collect source data first")
    rows = snapshot["rows"]
    if source == "shopify" and snapshot["mode"] == "live":
        return {
            "provider": "Deterministic validation",
            "classification": "inconclusive",
            "summary": "Order records were collected. Connect session measurements and a comparable baseline to assess checkout completion.",
        }
    ordered = sorted(rows, key=lambda r: r["date"])
    baseline = ordered[:-3]
    recent = ordered[-3:]
    if not baseline or not recent:
        raise ValueError("At least four daily rows are required")

    def rates(window):
        sessions = sum(r.get("sessions", 0) for r in window)
        orders = sum(r.get("orders", 0) for r in window)
        return {
            "sessions": sessions,
            "orders": orders,
            "completion_rate": orders / sessions if sessions else 0,
        }

    b, a = rates(baseline), rates(recent)
    daily_ratio = (
        (a["sessions"] / len(recent)) / (b["sessions"] / len(baseline))
        if b["sessions"]
        else 0
    )
    # This is a screening signal, not a regression verdict without release evidence.
    category = (
        "security_signal"
        if any(r.get("blocked_requests", 0) > 100 for r in recent)
        else (
            "data_quality"
            if any(r.get("collection_gap") for r in recent)
            else "traffic_anomaly" if daily_ratio > 2 else "inconclusive"
        )
    )
    summary = f"Completion rate changed from {b['completion_rate']:.1%} to {a['completion_rate']:.1%}. Release mapping is required to determine whether a code change contributed."
    if category == "security_signal":
        summary += " The fixture includes elevated blocked-request signals. This indicates a possible attack, not a confirmed compromise."
    if category == "data_quality":
        summary += " The fixture includes a purchase-event collection gap; validate instrumentation before assessing business impact."
    finding = {
        "title": "Source metric change",
        "summary": summary,
        "classification": category,
        "baseline": b,
        "actual": a,
        "evidence": [
            {
                "daily_session_ratio": round(daily_ratio, 2),
                "source": source,
                "mode": snapshot["mode"],
                "blocked_requests": sum(r.get("blocked_requests", 0) for r in recent),
                "collection_gap": any(r.get("collection_gap") for r in recent),
            }
        ],
        "commits": [],
        "cause": "No deployed commit mapping supplied",
        "segment": "Daily aggregate",
        "formula": "orders / sessions",
    }
    from investigator import investigate

    result = investigate(
        finding,
        engine.get("analysis_policy", "Check business outcomes and traffic changes."),
    )
    import uuid

    finding = {
        **result,
        "id": str(uuid.uuid4()),
        "source": source,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "measurements": {"baseline": b, "recent": a},
        "mode": snapshot["mode"],
    }
    from engine import LOCK

    with LOCK:
        engine.set(
            "source_findings", [finding] + engine.get("source_findings", [])[:49]
        )
        engine.audit("Source analyzed", source + ": " + result["classification"])
        engine.db.commit()
    return finding


def review_source(engine, body):
    action = body.get("action")
    statuses = {
        "resolve": "resolved",
        "ignore": "ignored",
        "not_issue": "not_issue",
        "reopen": "active",
    }
    if action not in statuses:
        raise ValueError("Unsupported review action")
    findings = engine.get("source_findings", [])
    finding = next((f for f in findings if f["id"] == body.get("finding_id")), None)
    if not finding:
        raise ValueError("Source finding not found")
    finding["status"] = statuses[action]
    finding["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    engine.set("source_findings", findings)
    engine.audit("Source finding reviewed", action)
    engine.db.commit()
    return state(engine)
