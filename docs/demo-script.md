# Five-minute demo: SME seller and banking

## Before presenting

Open http://127.0.0.1:8080. Click Run scenario, then Reset to healthy baseline. Keep the demo deck and app open. No cloud account or GitHub login is needed. The demo starts from healthy synthetic telemetry.

## 0:00–0:40 — The buyer's problem

“An engineering team can ship a change that leaves the service healthy but damages the business. Checkout succeeds less often, coupons erase profit, or delivery changes hurt retention. ImpactGuard helps developers investigate those outcomes and trace them back to the code.”

Buyer hypothesis: an independent Shopify seller with an agency or developer maintaining its storefront. Luma Goods is fictional. Seller impact projections assume 120 checkout starts/day at an $82 order value. The product earns its place by reducing investigation time and helping teams prioritize financially important regressions.

## 0:40–1:10 — Healthy system

Show Business issues. Explain the event count and observed revenue. Point out that this is synthetic traffic and a real persisted event pipeline.

Click Run scenario → Checkout regression.

“We introduced a payment redirect change. The detector evaluates observed customer outcomes against thirty days of baseline sessions.”

## 1:10–2:15 — Investigate

Open the checkout issue. Show conversion, affected segment, dollar formula and supporting evidence.

“The decline is concentrated in Safari sessions using PayPal. Other browser and payment combinations stay close to baseline. The dollar figure comes from code and explicit assumptions.”

Scroll to Suspect commits. Show the top SHA, reasons and diff.

“The candidate changed token handling in the PayPal redirect. Timing and affected files make it a strong investigation candidate. A ranking score supports the hypothesis. It doesn't prove causation.”

Click Investigate. “This offline demo uses evidence rules. The optional Vertex adapter uses the same evidence contract and labels its provider.”

## 2:15–3:00 — Respond and verify

Click Simulate remediation.

“This restores healthy behavior in the generator, then measures six thousand fresh sessions. The recovery is measured. It is not a cosmetic status toggle or a production rollback.”

Point to healthy conversion and recovered status. Return to Business issues.

## 3:00–3:35 — Broader business coverage

Run Promotion stacking. Show negative-margin orders and the suspect discount-combiner diff. Explain that uptime would remain healthy.

If time permits, remediate and run Delivery delays. Mention the mature synthetic cohort and annual projection assumptions.

## 3:35–4:30 — Banking reconciliation

Resolve the active commerce scenario. Open Reconciliation and run the banking scenario. Show 2,000 transfers, 200 mismatches, and $46,998.09 in unbacked credits. Open the suspect status-mapper commit.

“Failed and pending bank callbacks fall through to application success. ImpactGuard compares that flag with settlement evidence and ledger postings. It does not assume cash arrived because the app says success.”

Simulate remediation. Show 200 reversal entries, zero mismatches, and green reconciliation status. Original credit postings remain in the ledger. The engine also detects duplicate and missing postings.

## 4:30–5:00 — Why a team buys it

“The initial product fits between release tooling and business telemetry. Developers get a prioritized issue, a relevant diff, customer evidence, and a measured outcome. A pilot would test alert precision and investigation time before any claim about savings.”

Close with the next milestone: personal GCP deployment and one real repository plus one real checkout event stream. Do not imply cloud resources or connectors are already connected.

## Recovery plan

If the browser refreshes, findings persist in SQLite. If a scenario is already active, finish remediation or reset. If the model is unavailable, the labeled evidence-rule briefing remains available. No demo depends on external login or network access.
