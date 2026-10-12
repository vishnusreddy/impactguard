import json, os, mimetypes, pathlib, sys, traceback
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from engine import Engine, LOCK
from access import owner, public_preview

ROOT = pathlib.Path(__file__).resolve().parent.parent
store = None
if os.getenv("IMPACTGUARD_STORAGE_BUCKET"):
    from durable import DurableState

    store = DurableState()
engine = store.open() if store else Engine()


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
        global engine
        if (
            store
            and self.path.startswith("/api/")
            and not self.path.startswith("/api/health")
        ):
            try:
                with LOCK:
                    engine = store.refresh(engine)
            except Exception:
                return self.respond({"error": "State is temporarily unavailable"}, 503)
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.respond({"ok": True, "mode": "synthetic-demo"})
        if path == "/api/evaluation":
            return self.respond(
                json.loads((ROOT / "backend" / "evaluation_summary.json").read_text())
            )
        operator = owner(self.headers)
        if (
            public_preview()
            and not operator
            and path.startswith("/api/")
            and path != "/api/health"
        ):
            from public_demo import dashboard, connections, engine_for

            case = parse_qs(urlparse(self.path).query).get("scenario", ["checkout"])[0]
            try:
                with LOCK:
                    if path == "/api/dashboard":
                        return self.respond(dashboard(case, engine))
                    if path == "/api/github":
                        return self.respond(connections())
                    if path == "/api/export":
                        return self.respond(
                            {
                                "incident": engine_for(case).finding(),
                                "disclosure": "Generated public demo data only",
                            }
                        )
                    return self.respond({"error": "Owner access required"}, 403)
            except ValueError as e:
                return self.respond({"error": str(e)}, 400)
        if path == "/api/github":
            from connections import state

            with __import__("engine").LOCK:
                result = state(engine)
            return self.respond(result)
        if path == "/api/dashboard":
            data = engine.dashboard()
            data["deployment"].update(
                access="operator", public_preview=public_preview()
            )
            return self.respond(data)
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
        global engine
        with LOCK:
            return self.post_locked()

    def post_locked(self):
        global engine
        try:
            if store:
                engine = store.refresh(engine)
            before_changes = engine.db.total_changes
            origin = self.headers.get("Origin")
            proxy_origins = set(
                filter(None, os.getenv("IMPACTGUARD_ALLOWED_ORIGINS", "").split(","))
            )
            if (
                origin
                and origin not in proxy_origins
                and urlparse(origin).netloc != self.headers.get("Host")
            ):
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
            if public_preview() and not owner(self.headers):
                from public_demo import connections, analysis

                if path == "/api/metrics/discover":
                    return self.respond(
                        engine.get(
                            "public_metric_assessment",
                            {
                                "provider": "Awaiting prepared AI assessment",
                                "status": "unassessed",
                                "metrics": [],
                                "logging": [],
                                "questions": [],
                                "business_summary": "The generated assessment has not been prepared yet.",
                            },
                        )
                    )
                if path == "/api/investigate":
                    return self.respond(
                        analysis(engine, body.get("scenario", "checkout"))
                    )
                if path == "/api/integrations/collect" and body.get("sample") is True:
                    return self.respond(connections(body.get("scenario", "checkout")))
                if path == "/api/integrations/analyze":
                    return self.respond(
                        analysis(engine, body.get("scenario", "checkout"), source=True)
                    )
                return self.respond(
                    {
                        "error": "Owner access required. Public access uses isolated sample data."
                    },
                    403,
                )
            if path == "/api/metrics/discover":
                from metric_discovery import discover

                with LOCK:
                    result = discover(engine, body)
            elif path == "/api/demo/prepare":
                from public_demo import prepare

                result = prepare(engine)
            elif path == "/api/github/connect":
                from connections import connect

                with __import__("engine").LOCK:
                    result = connect(engine, body.get("repo", ""))
            elif path == "/api/integrations/config":
                from connections import configure

                with __import__("engine").LOCK:
                    result = configure(engine, body)
            elif path == "/api/integrations/collect":
                from connections import collect

                with __import__("engine").LOCK:
                    result = collect(engine, body)
            elif path == "/api/integrations/analyze":
                from connections import analyze

                result = analyze(engine, body)
            elif path == "/api/integrations/review":
                from connections import review_source

                with __import__("engine").LOCK:
                    result = review_source(engine, body)
            elif path == "/api/github/remove":
                from connections import state

                with __import__("engine").LOCK:
                    engine.set(
                        "project_repos",
                        [
                            r
                            for r in engine.get("project_repos", [])
                            if r["repo"] != body.get("repo")
                        ],
                    )
                    engine.db.commit()
                    result = state(engine)
            elif path == "/api/github/rank":
                from github_integration import rank_commits

                from connections import state

                commits = state(engine)["commits"]
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
                result = engine.investigate_finding(body.get("finding_id"))
            else:
                return self.respond({"error": "Not found"}, 404)
            if store and engine.db.total_changes != before_changes:
                try:
                    store.persist(engine)
                except Exception as persistence_error:
                    engine = store.refresh(engine, force=True)
                    if type(persistence_error).__name__ == "StateConflict":
                        return self.respond(
                            {
                                "error": "State changed in another instance; retry the request"
                            },
                            409,
                        )
                    return self.respond(
                        {"error": "State could not be saved; retry the request"}, 503
                    )
            self.respond(result)
        except (ValueError, TypeError) as e:
            self.respond({"error": str(e)}, 400)
        except Exception:
            print(
                "Request failed; sensitive provider details suppressed", file=sys.stderr
            )
            self.respond({"error": "Internal error. Check server logs."}, 500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"ImpactGuard running at http://127.0.0.1:{port}", flush=True)
    ThreadingHTTPServer((os.getenv("HOST", "127.0.0.1"), port), Handler).serve_forever()
