# backend/research/evaluation/metrics.py
"""Calculate metrics comparing LLM extraction to ground truth"""
import json
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = PROJECT_ROOT / "dataset"

@dataclass
class ExtractionMetrics:
    """Container for evaluation metrics"""
    precision: float
    recall: float
    f1: float
    exact_match: float
    argument_accuracy: float
    temporal_accuracy: float
    spatial_accuracy: float
    num_extracted: int
    num_ground_truth: int

class LexIntelEvaluator:
    def __init__(self, 
                 ground_truth_path: str | Path = DATASET_DIR / "ground_truth" / "annotations.jsonl",
                 extracted_events_path: str | Path = DATASET_DIR / "extracted_events.json"):
        
        self.ground_truth = self._load_ground_truth(ground_truth_path)
        self.extracted = self._load_extracted(extracted_events_path)
        
    def _load_ground_truth(self, path: str) -> Dict[str, List[Dict]]:
        """Load manually annotated ground truth"""
        gt = {}
        with open(path) as f:
            for line in f:
                annotation = json.loads(line)
                case_id = str(annotation['case_id'])
                if case_id not in gt:
                    gt[case_id] = []
                gt[case_id].extend(annotation['correct_events'])
        return gt
    
    def _load_extracted(self, path: str) -> Dict[str, List[Dict]]:
        """Load your LLM-extracted events"""
        with open(path) as f:
            extracted = json.load(f)
        
        if isinstance(extracted, dict) and isinstance(extracted.get("by_case"), dict):
            return {str(case_id): events for case_id, events in extracted["by_case"].items()}
        
        if isinstance(extracted, list):
            return {str(case['case_id']): case['events'] for case in extracted}
        
        raise ValueError(
            "Unsupported extracted events format. Expected a list or a dict with a by_case field."
        )
    
    def _normalize_event(self, event: Dict) -> Tuple[str, str, str, str]:
        """Create canonical representation for matching"""
        return (
            event.get('actor', '').lower().strip(),
            event.get('action', '').lower().strip(),
            event.get('time', '').lower().strip(),
            event.get('location', '').lower().strip()
        )
    
    def _calculate_argument_accuracy(self, pred: Dict, gold: Dict) -> Dict:
        """Calculate which arguments are correct"""
        return {
            'actor': pred.get('actor') == gold.get('actor'),
            'action': pred.get('action') == gold.get('action'),
            'time': pred.get('time') == gold.get('time'),
            'location': pred.get('location') == gold.get('location')
        }

    def _specific_argument_accuracy(self, pred_norm: Dict, gold_norm: Dict, argument: str) -> float:
        """Calculate one argument's accuracy across exactly matched events."""
        matched_keys = set(gold_norm.keys()) & set(pred_norm.keys())
        if not matched_keys:
            return 0.0
        
        correct = sum(
            1
            for key in matched_keys
            if pred_norm[key].get(argument) == gold_norm[key].get(argument)
        )
        return correct / len(matched_keys)
    
    def evaluate_case(self, case_id: str) -> ExtractionMetrics:
        """Evaluate extraction for a single case"""
        case_id = str(case_id)
        gold_events = self.ground_truth.get(case_id, [])
        pred_events = self.extracted.get(case_id, [])
        
        if not gold_events:
            return None
        
        # Convert to normalized form for matching
        gold_norm = {self._normalize_event(e): e for e in gold_events}
        pred_norm = {self._normalize_event(e): e for e in pred_events}
        
        # Calculate matches
        true_positives = set(gold_norm.keys()) & set(pred_norm.keys())
        false_positives = set(pred_norm.keys()) - set(gold_norm.keys())
        false_negatives = set(gold_norm.keys()) - set(pred_norm.keys())
        
        precision = len(true_positives) / (len(true_positives) + len(false_positives) + 1e-8)
        recall = len(true_positives) / (len(true_positives) + len(false_negatives) + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        
        # Calculate argument accuracy for matched events
        argument_correct = 0
        argument_total = 0
        for gold_key, gold_event in gold_norm.items():
            if gold_key in true_positives:
                pred_event = pred_norm[gold_key]
                arg_acc = self._calculate_argument_accuracy(pred_event, gold_event)
                argument_correct += sum(arg_acc.values())
                argument_total += len(arg_acc)
        
        argument_accuracy = argument_correct / (argument_total + 1e-8)
        
        # Exact match (all arguments correct)
        exact_matches = sum(1 for gold_key in true_positives 
                          if self._calculate_argument_accuracy(pred_norm[gold_key], gold_norm[gold_key])['actor'] and
                             self._calculate_argument_accuracy(pred_norm[gold_key], gold_norm[gold_key])['action'])
        exact_match = exact_matches / (len(true_positives) + 1e-8)
        
        return ExtractionMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            exact_match=exact_match,
            argument_accuracy=argument_accuracy,
            temporal_accuracy=self._specific_argument_accuracy(pred_norm, gold_norm, 'time'),
            spatial_accuracy=self._specific_argument_accuracy(pred_norm, gold_norm, 'location'),
            num_extracted=len(pred_events),
            num_ground_truth=len(gold_events)
        )
    
    def evaluate_all(self) -> pd.DataFrame:
        """Evaluate all annotated cases"""
        results = []
        for case_id in self.ground_truth.keys():
            metrics = self.evaluate_case(case_id)
            if metrics:
                result = asdict(metrics)
                result['case_id'] = case_id
                results.append(result)
        
        df = pd.DataFrame(results)
        
        # Print summary
        print("\n📊 Overall Performance Summary")
        print("="*50)
        print(f"Cases evaluated: {len(df)}")
        print(f"Average Precision: {df['precision'].mean():.3f} ± {df['precision'].std():.3f}")
        print(f"Average Recall: {df['recall'].mean():.3f} ± {df['recall'].std():.3f}")
        print(f"Average F1 Score: {df['f1'].mean():.3f} ± {df['f1'].std():.3f}")
        print(f"Argument Accuracy: {df['argument_accuracy'].mean():.3f}")
        
        return df
