# Connections and AI

Run `./scripts/start-local.sh`, then open http://127.0.0.1:8080.

## Demonstration

In Integrations, select a sample scenario, collect Shopify and GA4 samples, then select Analyze metrics. All sample records are generated locally. Checkout decline, traffic spike, possible attack signals, and a collection gap are separate cases. Samples never access an account. Imported records remain separate from the legacy demo dashboard.

Codebases accepts owner/repository or a GitHub URL. A project supports up to 10 repositories. Import reads the latest 10 commits and bounded diffs, excluding sensitive filenames and redacting known secret patterns. Public repositories need no token. Private repositories use an explicit `IMPACTGUARD_GITHUB_TOKEN` with read-only access. App code does not read `gh` authentication. Connecting a repository does not establish deployment attribution.

## Personal Vertex AI

Set these variables in the server's environment:

- `IMPACTGUARD_VERTEX_PROJECT`: your **personal** project ID.
- `IMPACTGUARD_VERTEX_CREDENTIALS`: absolute path to explicit personal service-account or isolated user credentials, outside Git or under ignored `.secrets/`.
- `GEMINI_MODEL`: a model enabled in that project.
- `IMPACTGUARD_VERTEX_LOCATION`: defaults to `global`.
- `IMPACTGUARD_AI_CALL_LIMIT`: defaults to 20 requests per server process.

Install optional dependencies with `python3 -m pip install -r backend/requirements-cloud.txt`. Use a virtual environment. Enable Vertex AI and grant the selected account the required Vertex permissions in the personal project. No deployment or work-account login is required. Ambient Google credentials are not used by these connectors.

AI runs only when an operator selects Run analysis or Analyze metrics. It receives redacted aggregate evidence and bounded candidate diffs, with configurable checks. It classifies business regressions, traffic anomalies, security signals, operational incidents, data quality, or inconclusive evidence; it also writes verification steps. Output is schema-checked and capped at 1,200 tokens. Identical requests are cached in memory. Detection in the legacy synthetic dashboard still uses deterministic screening; source analysis supports AI semantic detection and investigation. Arithmetic and ledger validation remain deterministic. No automatic remediation is performed.

## Shopify

Configure the `store.myshopify.com` domain in Integrations. Set `IMPACTGUARD_SHOPIFY_TOKEN` to a dedicated Admin API token with `read_orders`. Collection reads at most 500 orders from the last 14 days via Admin GraphQL 2026-10. It requests date, payment state, amount, and currency, without customer names, addresses, emails, or card details. A truncated result is identified in the response. Live order records alone cannot establish conversion: session data and comparable windows are required.

## GA4

Configure the numeric property ID. Set `IMPACTGUARD_GA_CREDENTIALS` to a dedicated service-account JSON file with access to that property. Enable the Analytics Data API in that personal project. Collection uses `analytics.readonly` and requests daily sessions, purchases, and revenue for the last 14 days. Reports may reflect collection delays and attribution definitions; they are not settlement evidence.

## Secrets and boundaries

Do not put credentials into analysis instructions or source code. `.env*`, `.secrets/`, keys, and credential JSON files are ignored. Known secret formats and assignments are redacted from imported diffs and model evidence. Authentication credentials are sent only to the intended provider for authentication, never included in model prompts or API responses. Pattern redaction is defense in depth, not a guarantee against every possible secret format. Review repository contents and keep credentials outside source control. Provider errors do not print raw responses or credentials.

The local server binds to loopback and is not a multi-user production service. No OAuth installation flow, scheduled ingestion, production deployment mapping, cross-source identity joins, or confirmed intrusion detection is implemented. Resolve, Ignore, Not an issue, and Reopen change review state only; evidence and ledger entries remain intact.
