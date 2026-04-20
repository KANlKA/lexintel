# backend/research/experiments/prompt_variants.py
"""Extend your existing prompt testing for research"""
import json
from pathlib import Path
from typing import List, Dict
import pandas as pd
from datetime import datetime

class PromptExperiment:
    """Systematic prompt testing for your research question"""
    
    PROMPT_TEMPLATES = {
        "baseline": """
        Extract all events from this legal document.
        Each event: actor, action, time, location.
        
        Document: {text}
        
        Output JSON: {{"events": [...]}}
        """,
        
        "legal_structured": """
        You are a legal analyst. Extract events following legal case structure.
        
        CRIME: [action]
        PERPETRATOR: [actor]  
        TIME: [when]
        LOCATION: [where]
        
        Document: {text}
        
        Output as JSON array.
        """,
        
        "chain_of_thought": """
        Analyze this legal document step by step:
        1. What actions occurred?
        2. Who performed each action?
        3. When did it happen? (time expressions)
        4. Where did it happen? (location mentions)
        
        Document: {text}
        
        Show your reasoning, then output JSON.
        """,
        
        "few_shot": """
        Example 1:
        Text: "The accused stabbed the victim at 9 PM in the parking lot"
        Output: {{"actor": "accused", "action": "stabbed", "time": "9 PM", "location": "parking lot"}}
        
        Example 2:
        Text: "Witness saw the defendant running away around midnight"
        Output: {{"actor": "defendant", "action": "running away", "time": "midnight", "location": ""}}
        
        Now extract from: {text}
        """
    }
    
    def __init__(self, groq_client):
        self.client = groq_client
        self.results = []
        
    async def run_experiment(self, test_cases: List[Dict], num_samples: int = 30):
        """
        Test all prompt variants on sample cases
        """
        for prompt_name, prompt_template in self.PROMPT_TEMPLATES.items():
            print(f"\n🔬 Testing prompt: {prompt_name}")
            
            for case in test_cases[:num_samples]:
                # Format prompt
                prompt = prompt_template.format(text=case['text'])
                
                # Call LLM (your existing Groq integration)
                start_time = datetime.now()
                extraction = await self._call_llm(prompt)
                latency = (datetime.now() - start_time).total_seconds()
                
                # Store result
                self.results.append({
                    'prompt_type': prompt_name,
                    'case_id': case['id'],
                    'num_events': len(extraction.get('events', [])),
                    'latency_seconds': latency,
                    'raw_output': extraction,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Save results
        df = pd.DataFrame(self.results)
        df.to_csv('results/prompt_experiment_results.csv', index=False)
        
        # Generate comparison
        self._generate_comparison_report(df)
        
        return df
    
    def _generate_comparison_report(self, df: pd.DataFrame):
        """Create comparison table for paper"""
        summary = df.groupby('prompt_type').agg({
            'num_events': ['mean', 'std'],
            'latency_seconds': ['mean', 'std']
        }).round(3)
        
        print("\n📊 Prompt Comparison Results")
        print(summary)
        
        # Save for paper
        summary.to_csv('results/prompt_comparison_for_paper.csv')