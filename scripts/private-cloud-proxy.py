#!/usr/bin/env python3
"""Loopback-only access to the private Cloud Run service using audience-bound tokens."""

import json, os, pathlib, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import requests
from google.auth import load_credentials_from_file, impersonated_credentials
from google.auth.transport.requests import Request

root = pathlib.Path(__file__).resolve().parent.parent
config = json.loads((root / ".local/production.json").read_text())
source_file = pathlib.Path(config["credentials"])
if json.loads(source_file.read_text()).get("account") != config["account"]:
    raise SystemExit("The selected credential file does not match the personal account")
url = config["url"].rstrip("/")
if urlparse(url).scheme != "https" or not urlparse(url).hostname.endswith(".run.app"):
    raise SystemExit("Only the selected HTTPS Cloud Run endpoint is allowed")
if not config["access_account"].endswith(
    "@" + config["project"] + ".iam.gserviceaccount.com"
):
    raise SystemExit("The access identity must belong to the selected personal project")
source, _ = load_credentials_from_file(
    str(source_file), scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
target = impersonated_credentials.Credentials(
    source_credentials=source,
    target_principal=config["access_account"],
    target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
identity = impersonated_credentials.IDTokenCredentials(
    target_credentials=target, target_audience=url, include_email=True
)
lock = threading.Lock()


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.forward()

    def do_POST(self):
        self.forward()

    def forward(self):
        origin = self.headers.get("Origin")
        if origin and origin not in ("http://127.0.0.1:8081", "http://localhost:8081"):
            self.send_error(403, "Cross-origin request blocked")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length < 0 or length > 1024 * 1024:
                self.send_error(413)
                return
            with lock:
                if not identity.valid:
                    identity.refresh(Request())
                token = identity.token
            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower()
                not in ("authorization", "host", "connection", "content-length")
            }
            headers["Authorization"] = "Bearer " + token
            response = requests.request(
                self.command,
                url + "/" + self.path.lstrip("/"),
                headers=headers,
                data=self.rfile.read(length) if length else None,
                timeout=300,
                allow_redirects=False,
            )
            body = response.content
            self.send_response(response.status_code)
            for k, v in response.headers.items():
                if k.lower() not in (
                    "connection",
                    "transfer-encoding",
                    "content-length",
                    "content-encoding",
                    "authorization",
                ):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send_error(502, "Private Cloud Run request failed")


print("Private Cloud Run access: http://127.0.0.1:8081", flush=True)
ThreadingHTTPServer(("127.0.0.1", 8081), Proxy).serve_forever()
