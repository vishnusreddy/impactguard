# Deploying ImpactGuard in a personal Google Cloud project

Nothing in this guide has been executed against Google Cloud. Use a personal billing account and a project you explicitly choose. Do not use the machine's current gcloud configuration.

## Initial deployment recommendation

Use one private Cloud Run service in `us-central1`, request-based billing, 1 vCPU, 512 MiB RAM, zero minimum instances, one maximum instance, and concurrency 1. This is a small shareable demo, with a cold start after inactivity. The current demo uses local SQLite: service restarts can reset its data. A maximum of one instance does not make local storage durable. Do not mount a Cloud Storage bucket as a live SQLite database.

For persistent records, first migrate the store to an appropriate durable database. Add Pub/Sub, BigQuery and Gemini after the initial deployment works. Do not create a Cloud SQL instance just for this disposable demo, because an always-on database adds a fixed monthly cost.

## Personal account setup

In a browser profile signed into your personal Google account, create a new project and link your personal billing account. Keep its project ID and personal account email handy. Billing setup may require accepting terms and adding a payment method, which you should do yourself.

Open a fresh terminal and use a separate gcloud credentials/config directory:

```bash
export CLOUDSDK_CONFIG="$HOME/.config/gcloud-impactguard-personal"
gcloud auth login YOUR_PERSONAL_GOOGLE_EMAIL
```

This isolates the login from your existing work configuration. Do not use `--update-adc`, and do not run a bare `gcloud init` in your regular work environment. All deployment commands below explicitly specify the personal email and project ID.

## Build and deploy the existing Dockerfile

From the repository root, after substituting your actual personal email and project ID:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  --account=YOUR_PERSONAL_GOOGLE_EMAIL --project=YOUR_PERSONAL_PROJECT_ID

gcloud run deploy impactguard \
  --source=. \
  --region=us-central1 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=1 \
  --concurrency=1 \
  --timeout=120 \
  --no-allow-unauthenticated \
  --set-env-vars=CLOUD_ENABLED=0 \
  --account=YOUR_PERSONAL_GOOGLE_EMAIL \
  --project=YOUR_PERSONAL_PROJECT_ID
```

Source deployment detects the Dockerfile and uses Cloud Build and Artifact Registry. Follow any required project-specific build/service-account role setup from the official source deployment guide. Do not grant broad roles to fix a build without first identifying the missing permission.

Keep the service private because the demo exposes reset and remediation endpoints and has no application login. Access it with an authenticated local proxy:

```bash
gcloud run services proxy impactguard \
  --region=us-central1 --port=8081 \
  --account=YOUR_PERSONAL_GOOGLE_EMAIL --project=YOUR_PERSONAL_PROJECT_ID
```

Open http://localhost:8081. Other reviewers need Cloud Run invoker access and their own authenticated access path. A public URL needs application authentication or explicit acceptance of a publicly resettable synthetic demo.

## Estimated cost, checked 10 October 2026

These are planning estimates for a small demo, not a guaranteed cap. Amounts are USD before tax, based on `us-central1`, default on-demand pricing and available free-tier allowances. The free tier is shared at billing-account level.

| Setup | Estimated monthly bill | Assumptions |
|---|---:|---|
| Existing synthetic demo on Cloud Run | $0–$5 | Occasional demo visits, min instances 0, few builds, small image, no paid database or load balancer |
| Small cloud pipeline plus Gemini | $10–$25 planning allowance | Small event volume, bounded query scans, around 1,000 short investigations/month, token limits, no always-on database |
| Production deployment | Requires a workload estimate | Traffic, persistence, retention, region, model, data scans and access architecture determine cost |

Cloud Run's request-based free tier includes 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests per month at the stated base pricing. Cloud Build currently includes 2,500 eligible default-pool e2-standard-2 build minutes. Artifact Registry includes 0.5 GiB of storage, with additional storage around $0.10/GiB-month. Internet egress and logs can also contribute to the bill.

For illustration, Gemini 3.8 Flash global standard pricing currently lists $0.75 per million input tokens and $3.75 per million output/reasoning tokens through 31 December 2026. At 3,000 input tokens and 1,000 total output/reasoning tokens per investigation, 1,000 investigations cost about $6.00 in model usage. Pricing rises on 1 January 2027, and availability must be checked before selecting a model. The existing adapter requires you to select the model explicitly.

BigQuery ordinary on-demand analysis includes 1 TiB/month free and storage includes 10 GiB/month free. ML/TimesFM anomaly detection has its own pricing and must not be assumed covered by the SQL analysis free tier. Pub/Sub basic delivery includes 10 GiB/month of throughput free, while BigQuery export subscriptions do not receive that allowance.

Configure a $10 monthly budget with alerts before deploying. An alerts-only budget is a notification, not a spending limit. Google now also documents spend-cap budgets for supported services; check account eligibility, covered services, and enforcement details before relying on one. Bound instance count, model output, query scans and event volume regardless.

## Official references

- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Cloud Run source deployment](https://docs.cloud.google.com/run/docs/deploying-source-code)
- [Isolated gcloud configurations](https://docs.cloud.google.com/sdk/docs/configurations)
- [Cloud Build pricing](https://cloud.google.com/build/pricing)
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)
- [Gemini pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing)
- [BigQuery pricing](https://cloud.google.com/bigquery/pricing)
- [Pub/Sub pricing](https://cloud.google.com/pubsub/pricing)
- [Budgets and spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets)
