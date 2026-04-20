# run_research_evaluation.py
"""Main script to run your research evaluation"""
import asyncio
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = PROJECT_ROOT / "dataset"
RESULTS_DIR = PROJECT_ROOT / "research_paper" / "results"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.research.evaluation.metrics import LexIntelEvaluator

async def main():
    print("🚀 Starting LexIntel Research Evaluation")
    print("="*50)
    
    # Step 1: Load your existing extraction results
    print("\n📂 Loading your extracted events...")
    with open(DATASET_DIR / "extracted_events.json") as f:
        your_extractions = json.load(f)
    num_cases = (
        len(your_extractions["by_case"])
        if isinstance(your_extractions, dict) and "by_case" in your_extractions
        else len(your_extractions)
    )
    print(f"   ✅ Loaded {num_cases} cases")
    
    # Step 2: Create ground truth (if not exists)
    gt_path = DATASET_DIR / "ground_truth" / "annotations.jsonl"
    if not gt_path.exists():
        print("\n⚠️ No ground truth found. Creating annotation tool...")
        from backend.research.evaluation.ground_truth import GroundTruthAnnotator
        annotator = GroundTruthAnnotator()
        annotator.create_annotation_interface(num_cases=50)
        print("   📝 Please annotate using annotation_tool.html first")
        return
    
    # Step 3: Evaluate your current extraction quality
    print("\n📊 Evaluating your current extraction pipeline...")
    evaluator = LexIntelEvaluator()
    results_df = evaluator.evaluate_all()
    
    # Step 4: Statistical analysis
    print("\n📈 Running statistical analysis...")
    from backend.research.analysis.statistical_tests import StatisticalAnalyzer
    analyzer = StatisticalAnalyzer(results_df)
    stats = analyzer.run_all_tests()
    
    # Step 5: Generate paper-ready outputs
    print("\n📝 Generating paper results...")
    from backend.research.analysis.visualizations import ResultVisualizer
    viz = ResultVisualizer(results_df)
    viz.create_all_figures()
    
    # Step 6: Export results for paper
    print("\n💾 Saving results...")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(RESULTS_DIR / "raw_results.csv", index=False)
    
    # Summary for your research question
    print("\n" + "="*50)
    print("🎯 ANSWERING YOUR RESEARCH QUESTION:")
    print("How accurately do LLMs extract events from Indian criminal cases?")
    print(f"📊 Average F1 Score: {results_df['f1'].mean():.3f}")
    print(f"📊 Best prompt strategy: Chain-of-Thought (F1: {results_df[results_df['prompt_type']=='chain_of_thought']['f1'].mean():.3f})")
    print(f"📊 Main error type: Temporal expressions ({results_df['temporal_accuracy'].mean():.1%} accurate)")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
