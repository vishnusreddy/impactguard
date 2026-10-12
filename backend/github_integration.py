"""Read-only GitHub adapter and transparent heuristic commit ranking.
No ambient gh credentials. Only an explicitly supplied ImpactGuard token is used.
"""

import json, os, re, urllib.request, urllib.error
from datetime import datetime
from security import redact, safe_file


def normalize_repo(value):
    value = (
        value.strip()
        .removeprefix("https://github.com/")
        .removesuffix("/")
        .removesuffix(".git")
    )
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]+", value
    ) or value.split("/")[-1] in (".", ".."):
        raise ValueError("Use owner/repository or a github.com repository URL")
    return value


def github_get(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ImpactGuard-local-demo",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("IMPACTGUARD_GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in [401, 403]:
            raise ValueError(
                "GitHub authentication or rate limit blocked the request. Configure an explicit ImpactGuard read-only token."
            )
        if error.code == 404:
            raise ValueError(
                "Repository not found or private. Configure an explicit ImpactGuard read-only token."
            )
        raise ValueError("GitHub request failed with status " + str(error.code))


def fetch_commits(repo):
    repo = normalize_repo(repo)
    items = github_get(f"repos/{repo}/commits?per_page=10")
    commits = []
    for item in items:
        detail = github_get(f"repos/{repo}/commits/{item['sha']}")
        commits.append(
            {
                "sha": item["sha"],
                "message": item["commit"]["message"].split("\n")[0],
                "author": item["commit"]["author"]["name"],
                "timestamp": item["commit"]["author"]["date"],
                "url": item["html_url"],
                "files": [
                    {
                        "filename": f["filename"],
                        "additions": f["additions"],
                        "deletions": f["deletions"],
                        "patch": redact(
                            f.get("patch", "Diff unavailable for this file")
                        )[:4000],
                    }
                    for f in detail.get("files", [])[:30]
                    if safe_file(f["filename"])
                ],
                "source": "GitHub",
                "repo": repo,
            }
        )
    return redact(commits)


DEMO_COMMITS = [
    {
        "sha": "e921bd05a3784d2948a0a92dd5043109fbe7415a",
        "message": "refactor(banking): unify payment callback statuses",
        "author": "Jamie Chen",
        "timestamp": "2026-10-10T14:02:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/banking/settlement-status-mapper.ts",
                "additions": 4,
                "deletions": 6,
                "patch": "@@ -31,4 +31,2 @@ function mapPaymentStatus(bankStatus) {\n- if (bankStatus === 'settled') return 'success';\n- if (bankStatus === 'failed') return 'failed';\n- return 'pending';\n+ return bankStatus === 'cancelled' ? 'failed' : 'success';\n }",
            }
        ],
    },
    {
        "sha": "a8f31c29481b42cdda759f330937ae08b3ae99cc",
        "message": "refactor(checkout): simplify PayPal return redirect",
        "author": "Alex Morgan",
        "timestamp": "2026-10-10T14:02:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/checkout/paypal-redirect.ts",
                "additions": 12,
                "deletions": 8,
                "patch": "@@ -42,5 +42,5 @@ export function completePayPalReturn(session) {\n- const token = sessionStorage.getItem('paypal_token');\n- return confirmOrder({ token, orderId: session.orderId });\n+ const token = new URLSearchParams(location.search).get('token');\n+ return confirmOrder({ token, orderId: session.orderId });\n }\n// Simulated regression: Safari return navigation can omit query token.",
            }
        ],
    },
    {
        "sha": "7d09b62b874658d703a29882ef7e57954faa2810",
        "message": "feat(marketing): refresh home page hero",
        "author": "Sam Rivera",
        "timestamp": "2026-10-10T13:48:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/marketing/hero.tsx",
                "additions": 6,
                "deletions": 2,
                "patch": "@@ -12,2 +12,2 @@\n- <h1>Shop the collection</h1>\n+ <h1>Discover the new collection</h1>",
            }
        ],
    },
    {
        "sha": "b429e0198347480e870f86581ac22690e5a052be",
        "message": "fix(catalog): normalize product labels",
        "author": "Jamie Chen",
        "timestamp": "2026-10-10T13:32:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/catalog/labels.ts",
                "additions": 3,
                "deletions": 1,
                "patch": "@@ -8,1 +8,1 @@\n- return label;\n+ return label.trim();",
            }
        ],
    },
    {
        "sha": "c516ee849abc42072faf24a718c4b9a4875f6001",
        "message": "feat(promotions): allow multiple campaign codes",
        "author": "Alex Morgan",
        "timestamp": "2026-10-10T14:02:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/promotions/discount-combiner.ts",
                "additions": 9,
                "deletions": 4,
                "patch": "@@ -21,2 +21,2 @@\n- const discount = Math.max(...coupons.map(c => c.percent));\n+ const discount = coupons.reduce((sum, c) => sum + c.percent, 0);\n  return subtotal * (1 - discount / 100);",
            }
        ],
    },
    {
        "sha": "d112a3aa489a302c0def419990055215bb2f0210",
        "message": "feat(delivery): prefer economy carrier for US orders",
        "author": "Sam Rivera",
        "timestamp": "2026-10-10T14:02:00+00:00",
        "source": "Synthetic fixture",
        "repo": "acme/commerce-demo",
        "files": [
            {
                "filename": "src/delivery/carrier-routing.ts",
                "additions": 7,
                "deletions": 3,
                "patch": "@@ -16,1 +16,1 @@\n- return fastestCarrier(order.destination);\n+ return cheapestCarrier(order.destination);",
            }
        ],
    },
]


def rank_commits(commits, scenario, anomaly_start="2026-10-10T14:09:00+00:00"):
    keywords = {
        "checkout": ["checkout", "paypal", "redirect", "token", "payment"],
        "promotion": ["promotion", "discount", "coupon", "campaign"],
        "delivery": ["delivery", "carrier", "routing", "economy"],
        "banking": ["banking", "settlement", "status", "failed", "payment"],
    }.get(scenario, [])
    if not isinstance(anomaly_start, str):
        raise ValueError("Provide anomaly_start as an ISO timestamp with timezone")
    try:
        onset = datetime.fromisoformat(anomaly_start.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid anomaly onset timestamp")
    if not onset.tzinfo:
        raise ValueError("Anomaly timestamp must include a timezone")
    ranked = []
    for commit in commits:
        when = datetime.fromisoformat(commit["timestamp"].replace("Z", "+00:00"))
        minutes = (onset - when).total_seconds() / 60
        paths = " ".join(f["filename"] for f in commit["files"]).lower()
        diff = " ".join(f["patch"] for f in commit["files"]).lower()
        matches = [
            k
            for k in keywords
            if k in paths or k in diff or k in commit["message"].lower()
        ]
        same_service = bool(keywords and keywords[0] in paths)
        temporal = max(0, 1 - minutes / 60) if 0 <= minutes <= 60 else 0
        association = min(len(matches) / 3, 1)
        # 30% timing, 30% service, 25% diff association, 15% affected segment signal.
        segment = (
            1
            if (scenario == "checkout" and "paypal" in paths)
            or (scenario == "promotion" and "discount" in diff)
            or (scenario == "delivery" and "carrier" in diff)
            or (scenario == "banking" and "failed" in diff)
            else 0
        )
        score = (
            0.3 * temporal
            + 0.3 * int(same_service)
            + 0.25 * association
            + 0.15 * segment
        )
        reasons = []
        if temporal:
            reasons.append(f"Committed {minutes:.0f} minutes before the anomaly")
        if same_service:
            reasons.append("Changed files belong to the affected service")
        if matches:
            reasons.append("Relevant diff terms: " + ", ".join(matches))
        if not reasons:
            reasons.append("No matching evidence within the analysis window")
        ranked.append(
            {
                **commit,
                "score": round(score, 2),
                "reasons": reasons,
                "factors": {
                    "timing": round(temporal, 2),
                    "service": int(same_service),
                    "diff_association": round(association, 2),
                    "segment": segment,
                },
                "eligible": temporal > 0 and association > 0,
            }
        )
    return sorted(ranked, key=lambda c: (c["eligible"], c["score"]), reverse=True)


def fetch_business_context(repo, revision, limit=4):
    """Read a bounded, pinned snapshot. Never execute repository code."""
    import base64
    from pathlib import PurePosixPath

    repo = normalize_repo(repo)
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Refresh the repository import to obtain a pinned commit")
    tree = github_get(f"repos/{repo}/git/trees/{revision}?recursive=1")
    extensions = {
        ".py",
        ".ts",
        ".tsx",
        ".jsx",
        ".js",
        ".go",
        ".java",
        ".rb",
        ".sql",
        ".graphql",
        ".prisma",
        ".cs",
        ".php",
    }

    def eligible(item):
        path = item.get("path", "")
        parts = PurePosixPath(path).parts
        return (
            item.get("type") == "blob"
            and item.get("mode") in ("100644", "100755")
            and not path.startswith("/")
            and ".." not in parts
            and safe_file(path)
            and not set(parts).intersection(
                {
                    "node_modules",
                    "vendor",
                    "dist",
                    "build",
                    ".local",
                    "fixtures",
                    "__pycache__",
                    "tests",
                    "test",
                    "__tests__",
                }
            )
            and not (
                PurePosixPath(path).name.startswith("test_")
                or ".test." in path
                or ".spec." in path
            )
            and (
                PurePosixPath(path).suffix in extensions or path.lower() == "readme.md"
            )
            and item.get("size", 0) <= 100000
        )

    items = [item for item in tree.get("tree", []) if eligible(item)]
    terms = (
        "engine",
        "service",
        "controller",
        "handler",
        "schema",
        "model",
        "order",
        "payment",
        "checkout",
        "settle",
        "ledger",
        "refund",
        "discount",
        "event",
        "analytics",
        "booking",
        "subscription",
        "invoice",
        "fulfill",
    )
    items.sort(key=lambda i: (-sum(t in i["path"].lower() for t in terms), i["path"]))
    files = []
    for item in items[:limit]:
        if not re.fullmatch(r"[a-f0-9]{40}", item.get("sha", "")):
            raise ValueError("Invalid GitHub blob reference")
        blob = github_get(f"repos/{repo}/git/blobs/{item['sha']}")
        if blob.get("encoding") != "base64" or blob.get("size", 0) > 100000:
            continue
        try:
            content = base64.b64decode(blob["content"]).decode("utf-8")
        except (UnicodeError, ValueError):
            continue
        lines = redact(content).splitlines()
        selected = set(range(min(8, len(lines))))
        for i, line in enumerate(lines):
            if re.search(
                r"(?i)emit|logger|record|save|insert|update|status|amount|order|settle|payment|refund|discount|schema|event",
                line,
            ):
                selected.update(range(max(0, i - 1), min(len(lines), i + 3)))
        excerpt = "\n".join(f"{i+1}: {lines[i]}" for i in sorted(selected))[:1800]
        files.append(
            {
                "repo": repo,
                "revision": revision,
                "file": item["path"],
                "excerpt": excerpt,
                "truncated": len(content) > len(excerpt),
                "last_line": (
                    int(excerpt.splitlines()[-1].split(":", 1)[0]) if excerpt else 0
                ),
            }
        )
    return {
        "repo": repo,
        "revision": revision,
        "eligible_files": len(items),
        "tree_truncated": bool(tree.get("truncated")),
        "files": files,
        "files_scanned": len(files),
        "coverage": "Bounded file excerpts; not a whole-codebase audit",
    }
