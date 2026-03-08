from dateutil import parser as dateparser

def parse_time(time_str: str | None):
    if not time_str:
        return None
    try:
        return dateparser.parse(time_str, fuzzy=True)
    except Exception:
        return None

def build_timeline(events: list[dict]) -> list[dict]:
    timed = []
    untimed = []
    for e in events:
        parsed = parse_time(e.get("time"))
        if parsed:
            timed.append({**e, "_parsed_time": parsed})
        else:
            untimed.append(e)
    timed.sort(key=lambda x: x["_parsed_time"])
    # Untimed events go to end with a flag
    for e in untimed:
        timed.append({**e, "_parsed_time": None, "time_uncertain": True})
    return timed