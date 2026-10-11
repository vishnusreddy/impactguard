"""Isolated, generated public datasets. No account data or paid anonymous calls."""

from engine import Engine
from connections import sample

CASES = ("checkout", "promotion", "delivery", "banking")
SOURCE_CASES = ("checkout", "traffic", "security", "data_quality")
_ENGINES = {}


def engine_for(case="checkout"):
    if case not in CASES:
        raise ValueError("Unsupported demo scenario")
    if case not in _ENGINES:
        e = Engine(":memory:")
        e.launch(case)
        _ENGINES[case] = e
    return _ENGINES[case]


def dashboard(case="checkout"):
    data = engine_for(case).dashboard()
    data["deployment"].update(access="public", public_preview=True)
    return data


def connections(case="checkout"):
    if case not in SOURCE_CASES:
        raise ValueError("Unsupported sample scenario")
    return {
        "project": "Luma Goods",
        "repos": [],
        "commits": [],
        "connected": False,
        "snapshots": {s: sample(s, case) for s in ("shopify", "analytics")},
        "findings": [],
        "config": {},
        "credentials": {"shopify": False, "analytics": False, "vertex": False},
        "policy": "Check checkout completion, settlement evidence, margins, traffic, and data quality.",
        "public_preview": True,
    }


def prepare(real):
    from investigator import investigate
    from connections import collect, analyze

    results = {}
    sources = {}
    for case in CASES:
        e = Engine(":memory:")
        try:
            results[case] = investigate(e.launch(case)["finding"])
        finally:
            e.db.close()
    e = Engine(":memory:")
    try:
        for case in SOURCE_CASES:
            collect(e, {"source": "analytics", "sample": True, "scenario": case})
            result = analyze(e, {"source": "analytics"})
            sources[case] = {
                k: result.get(k)
                for k in (
                    "provider",
                    "classification",
                    "summary",
                    "recommended_verification",
                    "limitation",
                    "usage",
                )
            }
    finally:
        e.db.close()
    real.set("public_ai_templates", results)
    real.set("public_source_templates", sources)
    real.audit(
        "Public demo prepared", "Cached AI investigations use generated fixtures only."
    )
    real.db.commit()
    return {"prepared": list(results), "source_cases": list(sources)}


def analysis(real, case, source=False):
    allowed = SOURCE_CASES if source else CASES
    if case not in allowed:
        raise ValueError("Unsupported demo scenario")
    result = real.get(
        "public_source_templates" if source else "public_ai_templates", {}
    ).get(case)
    if not result:
        return {
            "provider": "Deterministic demo",
            "classification": "inconclusive",
            "summary": "The cached AI investigation is not available yet.",
            "cached": True,
            "mode": "synthetic",
        }
    return {
        **result,
        "cached": True,
        "mode": "synthetic",
        "disclosure": "Cached Gemini analysis of generated demo evidence. No new model request was sent.",
    }
