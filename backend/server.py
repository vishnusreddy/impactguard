import json, os, mimetypes, pathlib, sys, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from engine import Engine

ROOT = pathlib.Path(__file__).resolve().parent.parent
engine = Engine()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if args and str(args[0]).startswith("GET /api/dashboard"):
            return
        super().log_message(format, *args)

    def respond(self, data, status=200):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.respond({"ok": True, "mode": "synthetic-demo"})
        if path == "/api/github":
            return self.respond(
                {
                    "repo": engine.get("github_repo"),
                    "commits": engine.get("github_commits", []),
                    "connected": bool(engine.get("github_repo")),
                }
            )
        if path == "/api/dashboard":
            return self.respond(engine.dashboard())
        if path == "/api/export":
            finding_id = parse_qs(urlparse(self.path).query).get("finding_id", [None])[
                0
            ]
            return self.respond(
                {
                    "incident": engine.finding(finding_id),
                    "audit": engine.dashboard()["audit"],
                    "disclosure": "Synthetic traffic. Exposure is a projection, correlation does not establish causality.",
                }
            )
        if path.startswith("/api/"):
            return self.respond({"error": "Not found"}, 404)
        target = (ROOT / "dist" / path.lstrip("/")).resolve()
        if not target.is_relative_to(ROOT / "dist"):
            return self.respond({"error": "Not found"}, 404)
        if not target.is_file():
            target = ROOT / "dist" / "index.html"
        if not target.exists():
            return self.respond(
                {"error": "Build frontend with npm run build first"}, 503
            )
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(target)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                return self.respond({"error": "Cross-origin mutation blocked"}, 403)
            length = int(self.headers.get("Content-Length", 0))
            if length < 0:
                raise ValueError("Invalid body length")
            if length > 1024 * 1024:
                return self.respond({"error": "Body too large"}, 413)
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object")
            path = urlparse(self.path).path
            if path == "/api/github/connect":
                from github_integration import fetch_commits, normalize_repo

                repo = normalize_repo(body.get("repo", ""))
                commits = fetch_commits(repo)
                with __import__("engine").LOCK:
                    engine.set("github_repo", repo)
                    engine.set("github_commits", commits)
                    engine.audit(
                        "GitHub repository synced",
                        repo + " read-only commit metadata and diffs imported.",
                    )
                    engine.db.commit()
                result = {"repo": repo, "commits": commits, "connected": True}
            elif path == "/api/github/rank":
                from github_integration import rank_commits

                commits = engine.get("github_commits", [])
                if not commits:
                    raise ValueError("Connect a repository first")
                result = {
                    "commits": rank_commits(
                        commits,
                        body.get("scenario", "checkout"),
                        body.get("anomaly_start"),
                    ),
                    "limitation": "Heuristic association. Requires deployed commit mapping for production attribution.",
                }
            elif path == "/api/scenarios":
                result = engine.launch(body.get("scenario"))
            elif path == "/api/reset":
                result = engine.reset()
            elif path == "/api/actions":
                result = engine.action(body.get("action"), body.get("finding_id"))
            elif path == "/api/events":
                result = engine.ingest(body)
            elif path == "/api/investigate":
                from investigator import investigate

                f = engine.finding(body.get("finding_id"))
                if not f:
                    raise ValueError("Launch a scenario first")
                result = investigate(f)
            else:
                return self.respond({"error": "Not found"}, 404)
            self.respond(result)
        except (ValueError, TypeError) as e:
            self.respond({"error": str(e)}, 400)
        except Exception:
            traceback.print_exc()
            self.respond({"error": "Internal error. Check server logs."}, 500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"ImpactGuard running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer((os.getenv("HOST", "127.0.0.1"), port), Handler).serve_forever()
