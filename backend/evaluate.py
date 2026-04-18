"""
Research evaluation for LexIntel contradiction detection.

Compares three approaches against human-labelled ground truth:
  A: Rule-based         (existing system)
  B: Embedding-based    (sentence-transformers)
  C: LLM reasoning      (Groq Llama 3.1)
  D: Hybrid B+C         (proposed approach)

Outputs precision, recall, F1 for each approach + ablation table.

Usage:
    cd LexIntel/backend
    python evaluate.py

Requirements:
    - dataset/ground_truth.json must exist (run generate_ground_truth.py first)
    - Both backend servers don't need to be running — imports directly
"""

import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from document_pipeline.pipeline import process_dataset
from reasoning_engine.contradiction_detector import detect_contradictions
from reasoning_engine.contradiction_embedding import detect_contradictions_embedding
from reasoning_engine.contradiction_llm import detect_contradictions_llm


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(
    detected: list[dict],
    gt_positive_pairs: set[tuple],
    all_pairs: list[tuple],
) -> dict:
    """
    Compute precision, recall, F1 for a set of detected contradictions
    against the ground truth positive pairs.
    """
    detected_pairs = {
        (c["event1_id"], c["event2_id"]) for c in detected
    }
    # Also check reversed pair order
    detected_pairs_norm = set()
    for e1, e2 in detected_pairs:
        detected_pairs_norm.add((min(e1, e2), max(e1, e2)))

    gt_norm = set()
    for e1, e2 in gt_positive_pairs:
        gt_norm.add((min(e1, e2), max(e1, e2)))

    tp = len(gt_norm & detected_pairs_norm)
    fp = len(detected_pairs_norm - gt_norm)
    fn = len(gt_norm - detected_pairs_norm)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    return {
        "precision":      round(precision, 3),
        "recall":         round(recall, 3),
        "f1":             round(f1, 3),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "detected_total": len(detected),
    }


def build_hybrid(detected_b: list[dict], detected_c: list[dict]) -> list[dict]:
    """Union of embedding and LLM results, deduplicated by pair."""
    seen = set()
    hybrid = []
    for c in detected_b + detected_c:
        pair = (
            min(c["event1_id"], c["event2_id"]),
            max(c["event1_id"], c["event2_id"]),
        )
        if pair not in seen:
            seen.add(pair)
            hybrid.append(c)
    return hybrid


# ── Main ──────────────────────────────────────────────────────────────────────

def run_evaluation():
    gt_path = Path("../dataset/ground_truth.json")
    if not gt_path.exists():
        print("ERROR: ground_truth.json not found.")
        print("Run: python generate_ground_truth.py")
        print("Then manually label the file and save as ground_truth.json")
        return

    print("Loading ground truth...")
    with open(gt_path) as f:
        ground_truth = json.load(f)

    print(f"Loaded {len(ground_truth)} annotated cases.\n")

    # Load all events once
    print("Loading events from dataset...")
    all_events = process_dataset("../dataset/text.data.jsonl", limit=20)
    events_by_case = {}
    for e in all_events:
        events_by_case.setdefault(e["source_document"], []).append(e)

    # Allow hand-labelled fixtures to carry their own stable events. This is
    # useful because pipeline-generated event IDs are UUID4 values and will
    # otherwise change between ground-truth generation and evaluation runs.
    for case_data in ground_truth:
        embedded_events = case_data.get("events", [])
        if embedded_events:
            events_by_case[case_data["case_id"]] = embedded_events

    # Per-case results
    case_results: list[dict] = []

    for case_data in ground_truth:
        case_id = case_data["case_id"]
        case_events = events_by_case.get(case_id, [])

        if not case_events:
            print(f"  Skipping {case_id} — no events in pipeline output")
            continue

        print(f"Evaluating case: {case_id} ({len(case_events)} events)")

        # Ground truth positive pairs for this case
        gt_positive = set()
        for pair in case_data.get("contradiction_pairs", []):
            if pair.get("human_label"):
                gt_positive.add((pair["event1_id"], pair["event2_id"]))

        all_pairs = [
            (e1["event_id"], e2["event_id"])
            for e1, e2 in combinations(case_events, 2)
        ]

        if not gt_positive:
            print(f"  Warning: no labelled contradictions for {case_id}")

        # Run all approaches
        print(f"  Running approach A (rule-based)...")
        detected_a = detect_contradictions(case_events)

        print(f"  Running approach B (embedding)...")
        detected_b = detect_contradictions_embedding(case_events)

        print(f"  Running approach C (LLM)...")
        detected_c = detect_contradictions_llm(case_events, max_pairs=30)

        detected_d = build_hybrid(detected_b, detected_c)

        case_results.append({
            "case_id": case_id,
            "gt_positives": len(gt_positive),
            "A": compute_metrics(detected_a, gt_positive, all_pairs),
            "B": compute_metrics(detected_b, gt_positive, all_pairs),
            "C": compute_metrics(detected_c, gt_positive, all_pairs),
            "D": compute_metrics(detected_d, gt_positive, all_pairs),
        })

    if not case_results:
        print("No cases evaluated. Check your ground truth file.")
        return

    # ── Print results ─────────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("CONTRADICTION DETECTION — EVALUATION RESULTS")
    print("=" * 70)

    approaches = {
        "A": "Rule-based (baseline)",
        "B": "Embedding-based",
        "C": "LLM reasoning",
        "D": "Hybrid B+C (proposed)",
    }

    print(f"\n{'Approach':<26} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>6} {'FP':>6} {'FN':>6}")
    print("-" * 70)

    summary_rows = {}

    for key, label in approaches.items():
        metrics_list = [r[key] for r in case_results]
        n = len(metrics_list)

        avg = {
            m: round(sum(r[m] for r in metrics_list) / n, 3)
            for m in ["precision", "recall", "f1",
                      "true_positives", "false_positives", "false_negatives"]
        }
        summary_rows[key] = avg

        print(
            f"{label:<26} "
            f"{avg['precision']:>10.3f} "
            f"{avg['recall']:>10.3f} "
            f"{avg['f1']:>10.3f} "
            f"{avg['true_positives']:>6.1f} "
            f"{avg['false_positives']:>6.1f} "
            f"{avg['false_negatives']:>6.1f}"
        )

    print("=" * 70)

    # ── Ablation study ────────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("ABLATION STUDY — F1 contribution of each component")
    print("=" * 70)
    print(f"\n{'Configuration':<30} {'F1':>10}  {'vs Baseline':>12}")
    print("-" * 55)

    baseline_f1 = summary_rows["A"]["f1"]
    ablation_configs = {
        "Rule-based only (baseline)": summary_rows["A"]["f1"],
        "Embedding only":             summary_rows["B"]["f1"],
        "LLM only":                   summary_rows["C"]["f1"],
        "Hybrid B+C (proposed)":      summary_rows["D"]["f1"],
    }

    for config, f1 in ablation_configs.items():
        delta = f1 - baseline_f1
        delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
        print(f"{config:<30} {f1:>10.3f}  {delta_str:>12}")

    print("=" * 70)

    # ── Per-case breakdown ────────────────────────────────────────────────────

    print("\n" + "=" * 70)
    print("PER-CASE F1 BREAKDOWN")
    print("=" * 70)
    print(f"\n{'Case':<15} {'GT Pairs':>10} {'Rule':>8} {'Embed':>8} {'LLM':>8} {'Hybrid':>8}")
    print("-" * 60)

    for r in case_results:
        print(
            f"{r['case_id'][:14]:<15} "
            f"{r['gt_positives']:>10} "
            f"{r['A']['f1']:>8.3f} "
            f"{r['B']['f1']:>8.3f} "
            f"{r['C']['f1']:>8.3f} "
            f"{r['D']['f1']:>8.3f}"
        )

    print("=" * 70)

    # ── Save full results ─────────────────────────────────────────────────────

    output = {
        "summary": {k: summary_rows[k] for k in approaches},
        "ablation": ablation_configs,
        "per_case": case_results,
    }

    output_path = Path("../dataset/evaluation_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nFull results saved to: {output_path}")
    print("\nUse these tables directly in your research paper / report.")


if __name__ == "__main__":
    run_evaluation()
