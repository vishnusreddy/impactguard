"""Verify owner access for a public demo without exposing account connections."""

import json, os, threading, time, urllib.request

_CACHE = {}
_UNTIL = 0
_LOCK = threading.Lock()


def public_preview():
    return os.getenv("IMPACTGUARD_PUBLIC_PREVIEW") == "1"


def owner(headers):
    if not public_preview():
        return True
    header = headers.get("Authorization", "")
    if not header.startswith("Bearer ") or header[7:].count(".") != 2:
        return False
    audience = os.getenv("IMPACTGUARD_ADMIN_AUDIENCE")
    account = os.getenv("IMPACTGUARD_ADMIN_ACCOUNT")
    if not audience or not account:
        return False
    global _CACHE, _UNTIL
    try:
        with _LOCK:
            if time.time() >= _UNTIL:
                with urllib.request.urlopen(
                    "https://www.googleapis.com/oauth2/v1/certs", timeout=10
                ) as response:
                    _CACHE = json.load(response)
                _UNTIL = time.time() + 1800
            certs = dict(_CACHE)
        from google.auth import jwt

        claims = jwt.decode(
            header[7:], certs=certs, audience=audience, clock_skew_in_seconds=10
        )
        return (
            claims.get("iss") in ("https://accounts.google.com", "accounts.google.com")
            and claims.get("email") == account
            and claims.get("email_verified") is True
        )
    except Exception:
        return False
