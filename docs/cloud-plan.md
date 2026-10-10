# Cloud migration, not executed

No cloud resources have been created. Do not use the existing work account. A later deployment must use a separate personal account and explicitly selected project.

## Phase 1: shareable authenticated demo

Deploy the existing Docker image to one Cloud Run service behind IAM authentication. Build and access it only using an isolated gcloud configuration and a specified personal account/project. Do not inherit the current machine's active project. Keep one instance for a demo, and replace ephemeral SQLite before relying on persistence. Cloud Run instances can restart and local data can disappear.

## Phase 2: real data boundary

Introduce Pub/Sub at the ingestion boundary, a normalizer with replay-safe event IDs, BigQuery partitioned event tables, and persisted findings. Store raw events append-only and deduplicate by event ID at aggregation. Separate production records from simulator records. Add tenant identity and scoped service accounts.

`infra/bigquery.sql` defines the proposed six tables, metrics view and a TimesFM detection query. It requires project substitution and execution only in the selected personal project. The SQL has been checked against current documentation but has not run in BigQuery.

## Phase 3: evidence investigation

Run the optional Google Gen AI SDK adapter with explicitly selected credentials. Choose a currently available model in the chosen project. Add request timeouts, retry policy, token budget, structured-output validation and source provenance. Keep numerical impact calculation outside the model.

## Phase 4: deployment and commit attribution

Use read-only GitHub integration for diffs and a verified deployment event for repository, SHA, service, rollout time and feature flags. Authenticate any webhook with an HMAC secret and verify its delivery ID before ingestion. A commit timestamp alone is not deployment evidence. Correlate anomalies only to changes that reached the affected environment.

## Production gate

SSO, tenant isolation, authorization for every action, non-ephemeral state, rate limiting, retention policy, observability, queue retries/dead letters, seasonal baselines and measured alert precision are required before real customer use. Keep actions advisory until operator ownership and rollback permissions are implemented.

## References

- https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- https://docs.cloud.google.com/pubsub/docs/pubsub-basics
- https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-detect-anomalies
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart
