"""
run_prompt_variants.py

Runs all three prompt variants (A, B, C) on the same cases used for
gold standard evaluation, saving separate extracted_events files for
each prompt.

Usage:
    cd LexIntel/backend
    python run_prompt_variants.py --limit 10
"""

import json
import argparse
from pathlib import Path
from document_pipeline.ingestion.dataset_loader import load_cases
from document_pipeline.extraction.event_extractor import extract_events

DATASET_PATH  = "../dataset/text.data.jsonl"
PROMPTS_DIR   = Path("document_pipeline/prompts")
OUTPUT_DIR    = Path("../dataset/variant_results")

PROMPT_FILES = {
    "A_baseline": "event_prompt.txt",
    "B_focused":  "event_prompt_b.txt",
    "C_fewshot":  "event_prompt_c.txt",
}

def run_variant(cases: list[dict], prompt_name: str, prompt_text: str) -> dict:
    by_case: dict[str, list] = {}
    all_events = []

    for case in cases:
        case_id = case["case_id"]
        text    = case["text"]

        print(f"  [{prompt_name}] Processing case: {case_id}")

        events = extract_events(
            text,
            prompt_template=prompt_text,
            source_document=case_id,
        )

        event_dicts = [e.model_dump() for e in events]
        by_case[case_id] = event_dicts
        all_events.extend(event_dicts)

    return {
        "prompt_variant": prompt_name,
        "total_cases":    len(by_case),
        "total_events":   len(all_events),
        "by_case":        by_case,
    }

def main(limit: int):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {limit} cases from dataset...")
    cases = load_cases(DATASET_PATH, limit=limit)
    print(f"Loaded {len(cases)} cases: {[c['case_id'] for c in cases]}")

    for variant_name, prompt_file in PROMPT_FILES.items():
        prompt_path = PROMPTS_DIR / prompt_file
        if not prompt_path.exists():
            print(f"WARNING: Prompt file not found: {prompt_path} — skipping {variant_name}")
            continue

        prompt_text = prompt_path.read_text(encoding="utf-8")
        print(f"\nRunning variant {variant_name}...")

        result = run_variant(cases, variant_name, prompt_text)

        out_path = OUTPUT_DIR / f"extracted_{variant_name}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)

        print(f"  Saved {result['total_events']} events → {out_path}")

    print("\nAll variants complete. Now run evaluate_extraction.py for each.")
    print("Example:")
    for variant_name in PROMPT_FILES:
        print(f"  python evaluate_extraction.py "
              f"--gold ../dataset/gold_standard.json "
              f"--extracted ../dataset/variant_results/extracted_{variant_name}.json "
              f"--label '{variant_name}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    main(args.limit)