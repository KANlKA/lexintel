import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from document_pipeline.extraction.event_extractor import extract_events
from document_pipeline.ingestion.dataset_loader import load_cases
from document_pipeline.preprocessing.section_splitter import split_sections

PROMPTS_DIR = Path(__file__).parent / "document_pipeline" / "prompts"
OUTPUT_DIR  = Path(__file__).parent.parent / "dataset"

def load_prompt(variant: str) -> str:
    path = PROMPTS_DIR / f"event_prompt_{variant}.txt"
    return path.read_text(encoding="utf-8")

def run_variant(variant: str, limit: int = 10):
    print(f"\n{'='*50}")
    print(f"Running Prompt {variant}")
    print(f"{'='*50}")

    prompt_template = load_prompt(variant)
    cases = load_cases(str(OUTPUT_DIR / "sample_cases.jsonl"), limit=limit)

    results = {}

    for i, case in enumerate(cases):
        case_id = str(case.get("case_id", i))
        text    = case.get("text", "")
        if not text:
            continue

        print(f"  Case {i+1}/{len(cases)}: {case_id}")

        sections = split_sections(text)
        combined = "\n\n".join(
            s for s in [sections.get("facts",""),
                        sections.get("witness",""),
                        sections.get("other","")]
            if s
        )

        # Pass the prompt variant directly into extract_events
        events = extract_events(
            combined,
            prompt_template=prompt_template,
            source_document=case_id
        )

        results[case_id] = [e.model_dump() for e in events]
        print(f"    Extracted {len(events)} events")

    out_path = OUTPUT_DIR / f"extracted_events_{variant}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {out_path}")
    return results

if __name__ == "__main__":
    for variant in ["C"]:
        run_variant(variant, limit=10)
    print("\nAll done. Now run: python evaluate_comparison.py")