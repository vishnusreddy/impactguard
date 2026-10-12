"""AI metric discovery from pinned code and field inventory; proposals only."""

import hashlib, json, re
from datetime import datetime, timezone
from security import redact
from investigator import _request, _object, _string


def strings():
    return {"type": "ARRAY", "items": _string()}


REF = _object({"id": _string(), "line": {"type": "INTEGER"}})
REFS = {"type": "ARRAY", "items": REF}
SCHEMA = _object(
    {
        "business_summary": _string(),
        "metrics": {
            "type": "ARRAY",
            "items": _object(
                {
                    "name": _string(),
                    "priority": _string(),
                    "business_question": _string(),
                    "definition": _string(),
                    "required_fields": strings(),
                    "readiness": {
                        "type": "STRING",
                        "enum": [
                            "available_aggregate",
                            "needs_instrumentation",
                            "needs_confirmation",
                        ],
                    },
                    "evidence_refs": REFS,
                    "limitations": _string(),
                    "sql_draft": _string(),
                }
            ),
        },
        "logging": {
            "type": "ARRAY",
            "items": _object(
                {
                    "event_name": _string(),
                    "when_to_emit": _string(),
                    "fields": strings(),
                    "purpose": _string(),
                    "deduplication": _string(),
                    "evidence_refs": REFS,
                }
            ),
        },
        "questions": strings(),
    }
)


def connector_inventory(snapshots):
    """Only field names and scalar types leave the app; no row values."""
    sources = []
    for source, snapshot in sorted(snapshots.items()):
        fields = {}
        for row in snapshot.get("rows", [])[:20]:
            for key, value in row.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    fields[key] = type(value).__name__
        sources.append(
            {
                "id": "connector:" + source,
                "source": source,
                "mode": snapshot.get("mode", "unknown"),
                "fields": redact(fields),
                "grain": "Collector rows; verify semantics before using ratios or joins",
            }
        )
    return sources


def sample_evidence():
    return {
        "assessment_version": 2,
        "business_context": "Generated example: independent storefront with online payments. No real repository or account is connected.",
        "code": [
            {
                "id": "code:1",
                "repo": "sample/storefront",
                "revision": "synthetic",
                "file": "src/payments.ts",
                "last_line": 5,
                "excerpt": "1: export function recordPayment(callback) {\n2:   const status = callback.status === 'settled' ? 'success' : 'pending';\n3:   savePayment({ orderId: callback.orderId, status, amountCents: callback.amountCents });\n4:   logger.info('payment processed');\n5: }",
                "truncated": False,
            }
        ],
        "connectors": [
            {
                "id": "connector:analytics",
                "source": "analytics",
                "mode": "synthetic",
                "fields": {
                    "date": "str",
                    "sessions": "int",
                    "orders": "int",
                    "revenue": "float",
                },
                "grain": "Daily aggregates, no user/session-level join keys",
            }
        ],
        "coverage": [
            {
                "repo": "sample/storefront",
                "coverage": "One generated excerpt, not an actual repository scan",
            }
        ],
    }


def assess(evidence):
    result = _request(
        "discover",
        redact(evidence),
        "Propose metrics and instrumentation only. Do not execute SQL or change code.",
        SCHEMA,
        2600,
    )
    if result is None:
        return {
            "provider": "AI unavailable",
            "business_summary": "Configure personal Vertex AI to assess code and source fields.",
            "metrics": [],
            "logging": [],
            "questions": [],
            "status": "unassessed",
            "coverage": evidence.get("coverage", []),
        }
    ids = {
        x["id"]: x for x in evidence.get("code", []) + evidence.get("connectors", [])
    }
    if (
        not isinstance(result.get("business_summary"), str)
        or not isinstance(result.get("questions"), list)
        or any(not isinstance(q, str) for q in result["questions"])
    ):
        raise ValueError("Invalid discovery output")
    for group in ("metrics", "logging"):
        if not isinstance(result.get(group), list) or len(result[group]) > 6:
            raise ValueError("Discovery recommendations exceed the bounded budget")
        for item in result[group]:
            required = (
                (
                    "name",
                    "priority",
                    "business_question",
                    "definition",
                    "readiness",
                    "limitations",
                    "sql_draft",
                )
                if group == "metrics"
                else ("event_name", "when_to_emit", "purpose", "deduplication")
            )
            if any(not isinstance(item.get(k), str) for k in required):
                raise ValueError("Invalid recommendation field")
            field_key = "required_fields" if group == "metrics" else "fields"
            if (
                not isinstance(item.get(field_key), list)
                or len(item[field_key]) > 20
                or any(not isinstance(v, str) for v in item[field_key])
            ):
                raise ValueError("Invalid field proposal")
            if group == "logging" and any(
                re.search(
                    r"(?i)password|secret|authorization|api.?key|access.?token|card.?number|cvv|email|phone|raw.?body|raw.?payload",
                    name,
                )
                for name in item[field_key]
            ):
                raise ValueError(
                    "Logging proposal includes a prohibited sensitive field"
                )
            refs = item.get("evidence_refs")
            if not isinstance(refs, list) or not refs:
                raise ValueError("Recommendations require supplied evidence references")
            for ref in refs:
                if not isinstance(ref, dict):
                    raise ValueError("Invalid evidence reference")
                source = ids.get(ref.get("id"))
                line = ref.get("line")
                if not source or type(line) is not int:
                    raise ValueError("Unknown discovery evidence reference")
                if "excerpt" in source:
                    known = {
                        int(l.split(":", 1)[0])
                        for l in source["excerpt"].splitlines()
                        if re.match(r"^\d+:", l)
                    }
                    if line not in known:
                        raise ValueError("Discovery cited an unavailable code line")
                elif line != 0:
                    raise ValueError("Connector references do not have code lines")
            if group == "metrics":
                schema_files = [
                    source
                    for source in evidence.get("code", [])
                    if source.get("file", "").endswith((".sql", ".prisma"))
                ]
                if item["sql_draft"] and not schema_files:
                    item["sql_draft"] = ""
                    item[
                        "limitations"
                    ] += " SQL omitted because no database schema was supplied; the formula remains a proposal."
                if item["readiness"] not in (
                    "available_aggregate",
                    "needs_instrumentation",
                    "needs_confirmation",
                ):
                    raise ValueError("Invalid metric readiness")
                if item["readiness"] == "available_aggregate":
                    known_fields = {
                        name
                        for ref in refs
                        for name in ids[ref["id"]].get("fields", {})
                    }
                    missing = [
                        name
                        for name in item["required_fields"]
                        if name.split(".")[-1] not in known_fields
                    ]
                    if missing:
                        item["readiness"] = "needs_instrumentation"
                        item["limitations"] += (
                            " Required fields absent from inspected connectors: "
                            + ", ".join(missing)
                        )
                if item["readiness"] == "available_aggregate" and not any(
                    r["id"].startswith("connector:") for r in refs
                ):
                    raise ValueError("Available metric lacks connector evidence")
    result.update(
        status="proposed",
        coverage=evidence.get("coverage", []),
        sources=[
            {k: v for k, v in source.items() if k != "fields"}
            for source in evidence.get("code", []) + evidence.get("connectors", [])
        ],
        generated_at=datetime.now(timezone.utc).isoformat(),
        disclosure="Proposals only. No metric enabled, SQL executed, logging added, or code changed. Bounded excerpts can miss relevant behavior.",
    )
    return result


def discover(engine, body):
    from github_integration import fetch_business_context

    context = body.get("business_context", "")
    if not isinstance(context, str) or len(context) > 1200:
        raise ValueError("Business context must be at most 1,200 characters")
    if body.get("sample") is True:
        evidence = sample_evidence()
    else:
        repos = engine.get("project_repos", [])
        snapshots = engine.get("integration_snapshots", {})
        if not repos and not snapshots:
            raise ValueError(
                "Connect a codebase or collect source data first, or use the generated example"
            )
        evidence = {
            "assessment_version": 2,
            "business_context": redact(context),
            "code": [],
            "connectors": connector_inventory(snapshots),
            "coverage": [],
        }
        remaining = 10
        for repo in repos:
            if not repo.get("commits"):
                evidence["coverage"].append(
                    {
                        "repo": repo["repo"],
                        "coverage": "No pinned commit available; re-import this repository",
                    }
                )
                continue
            if remaining <= 0:
                evidence["coverage"].append(
                    {
                        "repo": repo["repo"],
                        "coverage": "Not scanned: ten-file assessment budget reached",
                    }
                )
                continue
            cached = engine.get("code_contexts", {}).get(repo["repo"])
            revision = repo["commits"][0]["sha"]
            limit = min(remaining, max(1, 10 // len(repos)))
            scan = (
                cached
                if cached and cached["revision"] == revision
                else fetch_business_context(repo["repo"], revision, limit)
            )
            contexts = engine.get("code_contexts", {})
            contexts[repo["repo"]] = scan
            engine.set("code_contexts", contexts)
            evidence["coverage"].append({k: v for k, v in scan.items() if k != "files"})
            for f in scan["files"][:remaining]:
                evidence["code"].append(
                    {"id": "code:" + str(len(evidence["code"]) + 1), **f}
                )
                remaining -= 1
    key = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    previous = engine.get("metric_assessment", {})
    if previous.get("fingerprint") == key:
        return {**previous, "cached": True}
    result = assess(evidence)
    result["fingerprint"] = key
    engine.set("metric_assessment", result)
    if body.get("sample") is True:
        engine.set("public_metric_assessment", result)
    engine.audit(
        "Metric assessment", result["provider"] + ": proposals only; no SQL executed"
    )
    engine.db.commit()
    return result
