# Business metric assessment

Open **Codebases → Business metrics and instrumentation**. Connect repositories and/or collect integration data, describe business outcomes, and select **Assess connected sources**. The generated example is available without account connections. One fresh Gemini request creates the assessment; identical evidence is cached durably. Public visitors receive only a prepared generated assessment and cannot submit private context or trigger paid requests.

## Evidence and coverage

GitHub reads a pinned revision through the read-only [tree](https://docs.github.com/en/rest/git/trees#get-a-tree) and [blob](https://docs.github.com/en/rest/git/blobs#get-a-blob) endpoints. Up to ten safe source excerpts across the connected repositories enter one assessment. Filename prioritization selects likely business and schema files; within each selected file, bounded excerpts include relevant state changes and logging statements. This is a sampling strategy, not a complete code audit. Coverage reports include revision, eligible-file count, inspected-file count and tree truncation. Re-import a repository to assess a newer revision. Repository code is never executed.

Connectors contribute observed field names, scalar types and source mode. Row values, customer records, credentials and payment payloads are not included. Synthetic fields are labeled synthetic and do not establish a live connector's capabilities. A code variable alone does not prove an integration collects it.

## Outputs

Gemini proposes prioritized business questions, metric definitions, required fields, readiness and limitations. Definitions should specify units, time windows, exclusions, numerator/denominator, and deduplication/join semantics. Recommendations cite supplied code lines or connector inventory IDs; unknown references are rejected. `available_aggregate` means fields are present for a proposed calculation, not that monitoring has been enabled or the definition approved. Missing connector fields downgrade availability to `needs_instrumentation`.

Logging proposals describe the event, where/when to emit it, fields, correlation and deduplication. An example payment lifecycle event may need a stable event ID, authoritative provider transaction ID, opaque order ID, previous/new status, occurred-at timestamp, amount in integer minor units, currency, service and release SHA. Avoid credentials, card details, personal contact information and raw request/payment bodies. Do not turn an application acknowledgement into bank-settlement evidence.

Optional SQL remains an unexecuted draft. Without inspected SQL/Prisma schema evidence it is omitted. Even with schema evidence, no query has been validated against a business database or automatically executed. No metrics are activated, no scheduling is added and no instrumentation patches are applied by this feature. Business owners must confirm meanings before implementing the recommendations.

## Limits

The assessment can miss behavior outside the selected excerpts and cannot prove that an event is delivered or complete. Field names do not establish units, cardinality, identity compatibility, retention or freshness. Suggested definitions and logging events require human review. Existing anomaly examples still use predefined collectors; this assessment adds recommendations, not an automatic database-query execution service.
