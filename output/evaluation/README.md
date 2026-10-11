# Synthetic attribution evaluation

Gemini 3.5 Flash-Lite identified the planted commit and a valid file/line in **25/25** cases. The previous keyword/timing heuristic selected the target in **1/25**. No responses failed validation. Detection and attribution used **78,858 total tokens** across 50 requests.

Each case has five eligible commits, including one keyword-heavy logging decoy. The old function passes the same contract that the planted new function violates. Ground truth is generated independently of model responses. Invalid answers and errors count as incorrect. Fix/test drafts are never executed.

This is a small, controlled stress test, not representative production accuracy or proof of causation. The keyword decoy deliberately challenges the baseline. No claims about real customer accuracy follow from this result. Detection false-positive rates require separate healthy and non-regression controls.

The development-v1 archive retains the first diagnostic run: its before-code did not match the passing baseline, so it is not the formal benchmark. Dataset v2 corrected that fixture and standardized validation before the reported run. This is development-set evidence, not a held-out evaluation.

Reproduce: configure explicitly selected personal Vertex credentials, then run `IMPACTGUARD_AI_CALL_LIMIT=100 .local/venv/bin/python scripts/evaluate-ai.py --live`. Results resume from stored case IDs; use a separate output directory for a fresh run. See the script CLI options.

## Detection controls

Gemini returned the expected decision/category for 6/6 separately authored controls: stable metrics, planned traffic growth, a reconciled ledger, unexplained traffic spike, credential-stuffing signals, and missing purchase events. This small check does not estimate production false-positive rates. Raw decisions are in `detection-controls.json`.
