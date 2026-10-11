"""User-facing incident copy. This module does not change measurements or scores."""


def format_finding(finding):
    if not finding:
        return finding
    result = dict(finding)
    scenario = result.get("scenario")
    result.setdefault("classification", "operational_incident" if scenario == "delivery" else "business_regression")
    if scenario == "checkout":
        result.update(
            title="Checkout completion rate decreased",
            metric="Checkout completion rate",
            summary=(
                "Checkout completion decreased for Safari sessions that use PayPal. "
                "The release changed PayPal redirect handling seven minutes before the simulated decline. "
                "Completion rates for other segments remained near baseline. "
                "The release is a candidate cause. The available evidence does not establish causation."
            ),
        )
    elif scenario == "promotion":
        count = result.get("evidence", [{}])[0].get("value", "Orders")
        result.update(
            title="Negative margin from combined discounts",
            summary=(
                f"{count} in the sample have negative contribution margin. "
                "These orders applied WELCOME20 and SUMMER25. "
                "The combined discount reduced revenue below the assumed product cost. "
                "The weekly estimate scales the sample to 120 seller checkout starts per day."
            ),
        )
    elif scenario == "delivery":
        result.update(
            title="Lower repeat purchase rate after delivery delays",
            summary=(
                "Customers in the delayed-delivery cohort had a lower 30-day repeat purchase rate "
                "than customers in the on-time cohort. This comparison uses mature synthetic cohorts. "
                "Customer mix may account for part of the difference. "
                "The annual estimate assumes that the observed difference persists at the configured seller volume."
            ),
        )
    elif scenario == "banking":
        count = result.get("evidence", [{}])[0].get("value", "Transactions")
        result.update(
            title="Credits without confirmed settlement",
            summary=(
                f"At detection, {count} had an application status of success and a bank status of failed or pending. "
                "The ledger includes credits for these unsettled transactions. "
                "Review the settlement status mapper and reconcile the credits that lack settlement evidence."
            ),
        )
    if result.get("timeline"):
        titles = [
            "Release recorded",
            "Metric changed",
            "Detection threshold exceeded",
            "Analysis completed",
        ]
        result["timeline"] = [
            {
                **entry,
                "title": titles[index] if index < len(titles) else entry["title"],
                **(
                    {"detail": "Candidate commits ranked and impact calculated."}
                    if index == 3
                    else {}
                ),
            }
            for index, entry in enumerate(result["timeline"])
        ]
    if result.get("reasoning_provider") == "Evidence rules":
        result["reasoning_provider"] = "Rule-based analysis"
    result["confidence_label"] = "The candidate score is not a causal probability"
    return result
