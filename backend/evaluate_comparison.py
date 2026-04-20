import json
from pathlib import Path

DATASET_DIR = Path(__file__).parent.parent / "dataset"

def normalize(text):
    return text.lower().strip() if text else ""

def event_matches(extracted, gold):
    ext_actor  = normalize(extracted.get("actor",  ""))
    ext_action = normalize(extracted.get("action", ""))
    gld_actor  = normalize(gold.get("actor",  ""))
    gld_action = normalize(gold.get("action", ""))

    actor_match  = gld_actor  in ext_actor  or ext_actor  in gld_actor
    action_match = gld_action in ext_action or ext_action in gld_action

    return actor_match and action_match

def evaluate_variant(variant: str, gold_data: list) -> dict:
    path = DATASET_DIR / f"extracted_events_{variant}.json"
    with open(path) as f:
        extracted_data = json.load(f)

    total_gold = total_extracted = total_matched = 0

    for gold_case in gold_data:
        case_id     = gold_case["case_id"]
        gold_events = gold_case["correct_events"]
        ext_events  = extracted_data.get(str(case_id), [])

        matched = 0
        for g in gold_events:
            for e in ext_events:
                if event_matches(e, g):
                    matched += 1
                    break

        total_gold      += len(gold_events)
        total_extracted += len(ext_events)
        total_matched   += matched

    precision = total_matched / total_extracted if total_extracted else 0
    recall    = total_matched / total_gold      if total_gold      else 0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0)

    return {
        "variant":   variant,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1":        round(f1, 3),
        "extracted": total_extracted,
        "gold":      total_gold,
        "matched":   total_matched,
    }

if __name__ == "__main__":
    with open(DATASET_DIR / "gold_standard.json") as f:
        gold_data = json.load(f)

    print("\nPrompt Comparison — LexIntel")
    print("=" * 68)
    print(f"{'Prompt':<22} {'Precision':>10} {'Recall':>10} "
          f"{'F1':>10} {'Extracted':>10}")
    print("-" * 68)

    all_results = []
    labels = {
        "A": "A — Baseline",
        "B": "B — Structured",
        "C": "C — Few-shot"
    }

    for variant in ["A", "B", "C"]:
        r = evaluate_variant(variant, gold_data)
        all_results.append(r)
        print(f"{labels[variant]:<22} {r['precision']:>10.3f} "
              f"{r['recall']:>10.3f} {r['f1']:>10.3f} "
              f"{r['extracted']:>10}")

    print("=" * 68)

    with open(DATASET_DIR / "prompt_comparison_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\nSaved to dataset/prompt_comparison_results.json")