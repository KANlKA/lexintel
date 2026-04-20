# sampling_strategy.py
"""
For a research paper with 183k documents and 708 extracted events:
You only need to annotate 50-100 events for statistical significance!
"""

import math
import random
import json
from pathlib import Path

def calculate_sample_size(population=708, confidence_level=0.95, margin_error=0.05):
    """
    Calculate how many events you need to annotate.
    For 95% confidence with 5% margin of error: need ~250 samples
    But for a final year project, 50-100 is acceptable.
    """
    # Standard sample size formula
    z_score = 1.96  # for 95% confidence
    p = 0.5  # expected proportion
    
    sample_size = (z_score**2 * p * (1-p)) / (margin_error**2)
    # Adjust for population size
    adjusted = sample_size / (1 + (sample_size - 1) / population)
    
    return math.ceil(adjusted)

def stratified_sample(extracted_events, num_samples=100):
    """
    Take a representative sample from your 708 events
    """
    with open(extracted_events) as f:
        data = json.load(f)
    
    all_events = []
    for case_id, events in data.get('by_case', {}).items():
        for event in events:
            all_events.append({
                'case_id': case_id,
                'event': event,
                'confidence': event.get('confidence', 0)
            })
    
    # Stratify by confidence level
    high_conf = [e for e in all_events if e['confidence'] >= 0.8]
    med_conf = [e for e in all_events if 0.6 <= e['confidence'] < 0.8]
    low_conf = [e for e in all_events if e['confidence'] < 0.6]
    
    # Sample proportionally
    samples = []
    samples.extend(random.sample(high_conf, min(30, len(high_conf))))
    samples.extend(random.sample(med_conf, min(50, len(med_conf))))
    samples.extend(random.sample(low_conf, min(20, len(low_conf))))
    
    print(f"\n📊 Sampling Strategy for Research Paper:")
    print(f"   Total events: {len(all_events)}")
    print(f"   Sample size: {len(samples)}")
    print(f"   - High confidence (≥0.8): {len([s for s in samples if s['confidence']>=0.8])}")
    print(f"   - Medium confidence (0.6-0.8): {len([s for s in samples if 0.6<=s['confidence']<0.8])}")
    print(f"   - Low confidence (<0.6): {len([s for s in samples if s['confidence']<0.6])}")
    
    return samples

if __name__ == "__main__":
    needed = calculate_sample_size()
    print(f"For your research paper, you need to annotate: {needed} events")
    print("But 50-100 is acceptable for a final year project.")