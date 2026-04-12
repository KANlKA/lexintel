"""
Ground truth generator for LexIntel contradiction detection evaluation.

Run this ONCE to generate a ground_truth_template.json file.
Then manually read each case and fill in which pairs actually contradict.

Usage:
    cd LexIntel/backend
    python generate_ground_truth.py

Output:
    ../dataset/ground_truth_template.json  — fill this in manually
"""

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from document_pipeline.pipeline import process_dataset


def generate_template(dataset_path: str, limit: int = 10) -> None:
    print(f"Loading {limit} cases from dataset...")
    events = process_dataset(dataset_path, limit=limit)

    # Group events by case (source_document)
    by_case: dict[str, list[dict]] = {}
    for e in events:
        by_case.setdefault(e["source_document"], []).append(e)

    print(f"Found {len(by_case)} cases with events.")

    ground_truth = []

    for case_id, case_events in by_case.items():
        print(f"\n{'='*60}")
        print(f"Case: {case_id}  ({len(case_events)} events)")
        print(f"{'='*60}")

        # Print all events for this case so you can read them
        for i, e in enumerate(case_events):
            print(f"  [{i}] {e['actor']} → {e['action']}")
            print(f"       time: {e.get('time') or 'unknown'}")
            print(f"       location: {e.get('location') or 'unknown'}")
            print(f"       event_id: {e['event_id']}")
            print()

        # Generate all cross-document pairs as template
        cross_pairs = [
            (e1, e2)
            for e1, e2 in combinations(case_events, 2)
            if e1["source_document"] != e2["source_document"]
        ]

        same_doc_pairs = [
            (e1, e2)
            for e1, e2 in combinations(case_events, 2)
            if e1["source_document"] == e2["source_document"]
        ]

        # For single-document cases, still include all pairs
        all_pairs = cross_pairs if cross_pairs else [
            (e1, e2) for e1, e2 in combinations(case_events, 2)
        ]

        contradiction_pairs = []
        non_contradiction_pairs = []

        for e1, e2 in all_pairs[:20]:  # cap at 20 pairs per case
            pair_entry = {
                "event1_id":      e1["event_id"],
                "event2_id":      e2["event_id"],
                "event1_summary": f"{e1['actor']} → {e1['action']} ({e1.get('time') or '?'})",
                "event2_summary": f"{e2['actor']} → {e2['action']} ({e2.get('time') or '?'})",
                # ← YOU FILL THIS IN: change to true if these genuinely contradict
                "human_label":    False,
                "notes":          "",
                "type":           "",
            }
            non_contradiction_pairs.append(pair_entry)

        ground_truth.append({
            "case_id":                   case_id,
            "total_events":              len(case_events),
            "contradiction_pairs":       contradiction_pairs,
            "non_contradiction_pairs":   non_contradiction_pairs,
        })

    output_path = Path("../dataset/ground_truth_template.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Template saved to: {output_path}")
    print(f"{'='*60}")
    print("\nNEXT STEPS:")
    print("1. Open dataset/ground_truth_template.json")
    print("2. For each pair, read the event summaries carefully")
    print("3. Set 'human_label': true for pairs that genuinely contradict")
    print("4. Move contradicting pairs from non_contradiction_pairs to contradiction_pairs")
    print("5. Add 'notes' explaining why they contradict")
    print("6. Save as ground_truth.json (same folder)")
    print("\nAim for at least 15-20 true contradiction pairs across all cases.")


if __name__ == "__main__":
    dataset = "../dataset/text.data.jsonl"
    generate_template(dataset, limit=10)