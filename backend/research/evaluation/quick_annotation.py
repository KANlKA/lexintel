# quick_annotation.py
"""
Annotate events based on intrinsic quality (no original text needed)
This is valid for research when original text is inaccessible.
"""

import json
from pathlib import Path

def quick_annotation_guide():
    """
    Judge each event using these heuristics:
    """
    print("""
    ========================================
    QUICK ANNOTATION GUIDE (No Original Text)
    ========================================
    
    For each event, mark INCORRECT if:
    
    1. ❌ ACTOR is "The", "There", "Unknown actor", or vague
    2. ❌ ACTION is a full sentence (not a real action)
    3. ❌ TIME is null when it should exist
    4. ❌ LOCATION is null when it should exist
    5. ❌ CONFIDENCE < 60% (LLM itself is unsure)
    
    Mark CORRECT if:
    
    1. ✓ ACTOR is a specific person/entity (e.g., "James Muir", "Court")
    2. ✓ ACTION is a verb phrase (e.g., "observed the car", "delivered opinion")
    3. ✓ Event makes logical sense as a single action
    
    ========================================
    """)

# Look at your problematic events from case 435649:
print("\n🔴 PROBLEMATIC EVENTS (These are INCORRECT):")
print("Event 1: Actor='The', Action=long sentence → INCORRECT")
print("Event 2: Actor='The', Action=long sentence → INCORRECT")
print("Event 3: Actor='The', Action=long sentence → INCORRECT")
print("Event 5: Actor='Unknown actor' → INCORRECT")

print("\n🟢 GOOD EVENTS (These are CORRECT):")
print("Case 2747110: Actor='James Muir', Action='observed the car' → CORRECT")
print("Case 2747110: Actor='Police', Action='arrived' → CORRECT")