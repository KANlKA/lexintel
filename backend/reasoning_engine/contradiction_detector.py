from itertools import combinations

def detect_contradictions(events: list[dict]) -> list[dict]:
    contradictions = []
    for e1, e2 in combinations(events, 2):
        # Location conflict: same actor, same time, different location
        if (e1.get("actor") == e2.get("actor")
                and e1.get("time") and e1.get("time") == e2.get("time")
                and e1.get("location") and e2.get("location")
                and e1["location"] != e2["location"]):
            contradictions.append({
                "event1_id": e1["event_id"],
                "event2_id": e2["event_id"],
                "type": "location_conflict",
                "description": f"{e1['actor']} cannot be at {e1['location']} and {e2['location']} at {e1['time']}",
                "severity": "critical"
            })
    return contradictions