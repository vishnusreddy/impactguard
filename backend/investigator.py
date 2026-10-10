"""Optional real Vertex AI investigation. No model-generated financial values."""

import json, os


def investigate(finding):
    project = os.getenv("GCP_PROJECT")
    if not project or os.getenv("CLOUD_ENABLED") != "1":
        return {
            "provider": "Rule-based analysis",
            "summary": finding["summary"],
            "limitation": "Gemini is not configured. This explanation comes from deterministic evidence rules.",
        }
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise ValueError(
            "Provide explicitly selected credentials. Ambient gcloud credentials are disabled."
        )
    model = os.getenv("GEMINI_MODEL")
    if not model:
        raise ValueError(
            "Select an available Vertex model explicitly with GEMINI_MODEL"
        )
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True, project=project, location=os.getenv("GCP_LOCATION", "global")
    )
    evidence = {
        k: finding[k]
        for k in [
            "title",
            "segment",
            "cause",
            "evidence",
            "baseline",
            "actual",
            "formula",
        ]
    }
    response = client.models.generate_content(
        model=model,
        contents="Investigate this business anomaly using only this evidence. Explain observations, candidate causes, uncertainty, and verification steps. Use concise technical English, short declarative sentences, active voice, and standard American spelling. Avoid slogans, metaphors, and marketing language. Do not claim proven causation. Do not calculate or invent money. Return JSON with summary and recommended_verification. Evidence: "
        + json.dumps(evidence),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "summary": {"type": "STRING"},
                    "recommended_verification": {"type": "STRING"},
                },
                "required": ["summary", "recommended_verification"],
            },
        ),
    )
    result = json.loads(response.text)
    return {"provider": "Vertex AI / " + model, **result}
