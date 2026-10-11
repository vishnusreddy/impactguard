"""Bounded, conservative redaction before storage and model requests."""

import re

PATTERNS = [
    r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
    r"(?:AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|shpat_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,})",
    r"(?i)(?:password|secret|api[_-]?key|access[_-]?token|token)\s*[:=]\s*[\"\x27][^\"\x27]{8,}[\"\x27]",
]


def redact(value):
    if isinstance(value, str):
        for pattern in PATTERNS:
            value = re.sub(pattern, "[REDACTED]", value)
        return value[:12000]
    if isinstance(value, list):
        return [redact(v) for v in value[:100]]
    if isinstance(value, dict):
        return {
            k: (
                "[REDACTED]"
                if re.search(
                    r"(?i)^(password|secret|api_key|access_token|authorization|credentials|token|apiKey|accessToken|client_secret)$",
                    k,
                )
                else redact(v)
            )
            for k, v in value.items()
        }
    return value


def safe_file(path):
    return not re.search(
        r"(?i)(^|/)(\.env[^/]*|credentials[^/]*|service.account[^/]*|secrets?[^/]*)|\.(pem|key|p12|pfx)$",
        path,
    )
