def score_weakness(event: dict, contradictions: list[dict]) -> dict:
    score = 0.0
    reasons = []

    involved = [c for c in contradictions
                if event["event_id"] in (c["event1_id"], c["event2_id"])]
    if involved:
        score += 0.5 * len(involved)
        reasons.append(f"involved in {len(involved)} contradiction(s)")

    if not event.get("time"):
        score += 0.2
        reasons.append("missing time")

    if not event.get("location"):
        score += 0.1
        reasons.append("missing location")

    if event.get("confidence", 1.0) < 0.7:
        score += 0.3
        reasons.append("low confidence extraction")

    return {
        "event_id": event["event_id"],
        "weakness_score": min(round(score, 2), 1.0),
        "reasons": reasons
    }