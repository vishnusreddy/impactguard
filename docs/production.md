# Production deployment

Public demo: https://impactguard-182850660018.us-central1.run.app/

The deployment uses the personal ImpactGuard project, Cloud Run in us-central1, and Cloud Storage checkpoints. Firebase dynamic hosting also uses Cloud Run; an additional hosting layer is unnecessary for this Python backend.

## Public and owner access

Anonymous visitors see isolated, generated datasets. They can switch scenarios, inspect candidate commits, and request cached Gemini explanations. Public requests cannot connect repositories or accounts, alter review states, read private project data, or trigger new paid model requests.

Owner access uses `scripts/private-cloud-proxy.py`, which binds only to 127.0.0.1:8081. Its ignored `.local/production.json` configuration selects the personal credential file and a dedicated access identity. Tokens are audience-bound to this Cloud Run service, kept in memory, and never printed. The backend verifies signed Google tokens before returning private data or accepting administrative actions. No work-account configuration is used.

Start owner access with `.local/venv/bin/python scripts/private-cloud-proxy.py`. Open http://127.0.0.1:8081. The selected personal credential must match the configured account. The public demo is separate from this owner workspace.

## State and cost

Cloud Run uses request-based billing, zero minimum instances, one maximum instance, concurrency one, one CPU, and 512 MiB memory. There is no always-on SQL database or load balancer. Successful mutations save a compressed SQLite checkpoint to a private Cloud Storage bucket. Generation preconditions reject conflicting writes across overlapping revisions. A new instance restores the saved checkpoint; SQLite is not opened on a Storage filesystem mount.

This is a low-volume deployment for one owner. Move to a transactional database before enabling concurrent writers or multiple owners. Private project data is durable; public fixture datasets are generated and read-only. Cached public AI explanations are persisted with the private checkpoint.

The target is light-use costs within the approved $5/month budget, subject to usage and billing-account free-tier eligibility. Project-scoped alerts are configured at INR 300 with 50%, 90%, and 100% thresholds. Alerts are not hard spending caps. Model output is limited to 1,200 tokens, requests are cached, and live analysis has a 20-attempt budget per process. Anonymous model requests only return prepared demo explanations.

The build and runtime use separate service accounts. The runtime can use Vertex AI and its private state bucket. The build identity can write container images, read build source, and write logs. Build source is allowlisted in `.gcloudignore`; credentials, local data, and `.local` configuration are excluded from uploads and Docker images. Source archives expire after seven days.

References: [Cloud Run pricing](https://cloud.google.com/run/pricing), [Firebase dynamic hosting](https://firebase.google.com/docs/hosting/cloud-run), [private service authentication](https://docs.cloud.google.com/run/docs/authenticating/developers).

## LLM detection release

Revision `impactguard-00006-cmk` serves the LLM-first pipeline. Public fixtures contain cached Gemini anomaly decisions, validated commit/file/new-line references, and unapplied fix/test drafts. The current banking fixture has five account review flags; these are not fraud determinations or blocks. Public mutation requests were verified as HTTP 403. The 25-case synthetic development evaluation and six detector controls are tracked in `output/evaluation/`; no production accuracy is claimed.
