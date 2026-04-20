print("RUN_EXTRACTION STARTED")
import json
from document_pipeline.pipeline import process_dataset

def process_dataset(dataset_path, limit=None):
    """
    Load dataset, extract events for each case,
    and return a flat list of events.
    """

    print(f"[Pipeline] Loading dataset: {dataset_path} (limit={limit})")

    cases = []

    try:
        with open(dataset_path, "r") as f:

            for i, line in enumerate(f):

                if limit and len(cases) >= limit:
                    break

                line = line.strip()

                if not line:
                    continue

                try:
                    case = json.loads(line)

                except json.JSONDecodeError:
                    print("Skipping invalid JSON line")
                    continue

                # ---- FIXED FIELD HANDLING ----

                case_id = case.get("case_id") or case.get("id")
                text = case.get("text")

                # Debug visibility
                if not case_id or not text:
                    print("Skipping case due to missing fields:", case.keys())
                    continue

                cases.append({
                    "id": str(case_id),
                    "text": text
                })

    except FileNotFoundError:
        print(f"Dataset file not found: {dataset_path}")
        return []

    print(f"[Pipeline] Loaded {len(cases)} cases")

    all_events = []

    # ---- EVENT EXTRACTION LOOP ----

    for case in cases:

        case_id = case["id"]
        text = case["text"]

        try:
            events = extract_events(text)

            # Attach case id to each event
            for event in events:
                event["source_document"] = case_id

            all_events.extend(events)

        except Exception as e:
            print(f"Error processing case {case_id}: {e}")

    print(f"[Pipeline] Total events extracted: {len(all_events)}")

    return all_events