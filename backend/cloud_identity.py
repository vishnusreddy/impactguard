"""Explicit local credentials or an explicitly selected Cloud Run service identity."""

import os


def configured():
    return bool(
        os.getenv("IMPACTGUARD_VERTEX_PROJECT")
        and os.getenv("GEMINI_MODEL")
        and (os.getenv("IMPACTGUARD_VERTEX_CREDENTIALS") or runtime_ready())
    )


def runtime_ready():
    project = os.getenv("IMPACTGUARD_VERTEX_PROJECT")
    account = os.getenv("IMPACTGUARD_RUNTIME_ACCOUNT", "")
    return bool(
        os.getenv("K_SERVICE")
        and project
        and os.getenv("GOOGLE_CLOUD_PROJECT") == project
        and account.endswith("@" + project + ".iam.gserviceaccount.com")
    )


def credentials():
    path = os.getenv("IMPACTGUARD_VERTEX_CREDENTIALS")
    if path:
        from google.auth import load_credentials_from_file

        return load_credentials_from_file(
            path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )[0]
    if runtime_ready():
        from google.auth.compute_engine import Credentials

        return Credentials(
            service_account_email=os.environ["IMPACTGUARD_RUNTIME_ACCOUNT"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
    raise ValueError(
        "Explicit credentials or a selected personal Cloud Run identity are required"
    )
