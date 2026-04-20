# backend/research/evaluation/ground_truth.py
"""Manual annotation tool for creating ground truth from your extracted events"""
import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os

class GroundTruthAnnotator:
    def __init__(self, 
                 extracted_events_path: str = "../dataset/extracted_events.json",
                 raw_data_path: str = "../dataset/text.data.jsonl"):
        
        # Adjust paths to find dataset
        base_dir = Path(__file__).parent.parent.parent
        
        extracted_path = base_dir / extracted_events_path
        raw_path = base_dir / raw_data_path
        
        print(f"Looking for extracted events at: {extracted_path}")
        print(f"Looking for raw data at: {raw_path}")
        
        if not extracted_path.exists():
            raise FileNotFoundError(f"Could not find {extracted_path}")
        if not raw_path.exists():
            raise FileNotFoundError(f"Could not find {raw_path}")
        
        with open(extracted_path) as f:
            self.extracted_events = json.load(f)
        
        self.raw_cases = self._load_raw_cases(str(raw_path))
        self.annotations = []
        
    def _load_raw_cases(self, path: str) -> List[Dict]:
        """Load original case documents"""
        cases = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
        return cases
    
    def create_annotation_interface(self, num_cases: int = 10):
        """
        Generate an HTML interface for manual annotation
        """
        # Select random cases from your extracted_events
        if isinstance(self.extracted_events, dict) and 'cases' in self.extracted_events:
            cases_list = self.extracted_events['cases']
        elif isinstance(self.extracted_events, list):
            cases_list = self.extracted_events
        else:
            cases_list = [self.extracted_events]
        
        selected_cases = random.sample(cases_list, min(num_cases, len(cases_list)))
        
        # Prepare data for HTML
        cases_data = []
        for case in selected_cases:
            case_data = {
                'id': case.get('case_id', case.get('id', 'unknown')),
                'events': case.get('events', [])
            }
            # Find corresponding raw text
            raw_case = next((c for c in self.raw_cases if c.get('id') == case_data['id']), None)
            case_data['text'] = raw_case.get('text', '')[:1000] if raw_case else 'Text not found'
            cases_data.append(case_data)
        
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>LexIntel Ground Truth Annotation</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .case { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .case-header { background: #2c3e50; color: white; padding: 10px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }
        .event { background: #f9f9f9; margin: 10px 0; padding: 15px; border-left: 4px solid #3498db; }
        .event.correct { border-left-color: #27ae60; background: #e8f5e9; }
        .event.incorrect { border-left-color: #e74c3c; background: #fdecea; }
        .event-field { display: inline-block; margin: 5px 10px; padding: 5px; background: #ecf0f1; border-radius: 4px; }
        button { margin: 5px; padding: 8px 15px; cursor: pointer; background: #3498db; color: white; border: none; border-radius: 4px; }
        button:hover { background: #2980b9; }
        .correct-btn { background: #27ae60; }
        .correct-btn:hover { background: #229954; }
        .incorrect-btn { background: #e74c3c; }
        .incorrect-btn:hover { background: #c0392b; }
        .actions { margin-top: 15px; }
        .save-btn { background: #2c3e50; padding: 10px 20px; font-size: 16px; }
        .progress { background: #ecf0f1; padding: 10px; margin-bottom: 20px; border-radius: 4px; }
        .text-preview { background: #fef9e7; padding: 15px; margin: 15px 0; border-left: 4px solid #f39c12; font-size: 14px; line-height: 1.6; }
        .annotation-status { margin-top: 10px; font-size: 14px; color: #7f8c8d; }
    </style>
</head>
<body>
    <h1>📝 LexIntel Ground Truth Annotation Tool</h1>
    <div class="progress" id="progress">Loading...</div>
    <div id="annotation-container"></div>
    <div style="position: fixed; bottom: 20px; right: 20px;">
        <button class="save-btn" onclick="saveAllAnnotations()">💾 Save All Annotations</button>
    </div>

    <script>
        const cases = """ + json.dumps(cases_data) + """;
        let currentIndex = 0;
        let annotations = {};
        
        function renderCase() {
            if (currentIndex >= cases.length) {
                document.getElementById('annotation-container').innerHTML = '<h2>✅ All cases annotated!</h2><p>Click "Save All Annotations" to download your work.</p>';
                document.getElementById('progress').innerHTML = `Completed ${cases.length} of ${cases.length} cases! 🎉`;
                return;
            }
            
            const case_ = cases[currentIndex];
            const annotated = annotations[case_.id] || {};
            
            document.getElementById('progress').innerHTML = `Case ${currentIndex + 1} of ${cases.length} | ${Object.keys(annotations).length} cases completed so far`;
            
            let eventsHtml = '';
            case_.events.forEach((event, idx) => {
                const isCorrect = annotated[idx] === true;
                const isIncorrect = annotated[idx] === false;
                const statusClass = isCorrect ? 'correct' : (isIncorrect ? 'incorrect' : '');
                
                eventsHtml += `
                    <div class="event ${statusClass}">
                        <strong>Event ${idx + 1}:</strong><br>
                        <div class="event-field">👤 Actor: ${event.actor || '?'}</div>
                        <div class="event-field">⚡ Action: ${event.action || '?'}</div>
                        <div class="event-field">⏰ Time: ${event.time || '?'}</div>
                        <div class="event-field">📍 Location: ${event.location || '?'}</div>
                        <div class="actions">
                            <button class="correct-btn" onclick="annotateEvent(${idx}, true)">✓ Correct</button>
                            <button class="incorrect-btn" onclick="annotateEvent(${idx}, false)">✗ Incorrect</button>
                        </div>
                        <div class="annotation-status">
                            ${annotated[idx] === true ? '✓ Marked as correct' : (annotated[idx] === false ? '✗ Marked as incorrect' : 'Not annotated yet')}
                        </div>
                    </div>
                `;
            });
            
            const html = `
                <div class="case">
                    <div class="case-header">
                        <h3>Case ID: ${case_.id}</h3>
                    </div>
                    <div class="text-preview">
                        <strong>📄 Document Preview:</strong><br>
                        ${case_.text.substring(0, 800)}${case_.text.length > 800 ? '...' : ''}
                    </div>
                    <h4>Extracted Events:</h4>
                    ${eventsHtml}
                    <div style="margin-top: 20px;">
                        <button onclick="previousCase()">◀ Previous</button>
                        <button onclick="nextCase()" style="background: #27ae60;">Next ▶</button>
                    </div>
                </div>
            `;
            
            document.getElementById('annotation-container').innerHTML = html;
        }
        
        function annotateEvent(eventIdx, isCorrect) {
            const case_ = cases[currentIndex];
            if (!annotations[case_.id]) {
                annotations[case_.id] = {};
            }
            annotations[case_.id][eventIdx] = isCorrect;
            renderCase();
        }
        
        function nextCase() {
            currentIndex++;
            renderCase();
        }
        
        function previousCase() {
            if (currentIndex > 0) {
                currentIndex--;
                renderCase();
            }
        }
        
        function saveAllAnnotations() {
            const output = [];
            for (const caseId in annotations) {
                const caseData = cases.find(c => c.id === caseId);
                if (caseData) {
                    const correctEvents = [];
                    const annotation = annotations[caseId];
                    for (let i = 0; i < caseData.events.length; i++) {
                        if (annotation[i] === true) {
                            correctEvents.push(caseData.events[i]);
                        }
                    }
                    output.push({
                        case_id: caseId,
                        correct_events: correctEvents,
                        total_events: caseData.events.length,
                        annotation_complete: Object.keys(annotation).length === caseData.events.length
                    });
                }
            }
            
            const blob = new Blob([output.map(o => JSON.stringify(o)).join('\\n')], {type: 'application/jsonl'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ground_truth_${new Date().toISOString().slice(0,19)}.jsonl`;
            a.click();
            URL.revokeObjectURL(url);
            
            alert(`✅ Saved ${output.length} case annotations!`);
        }
        
        renderCase();
    </script>
</body>
</html>"""
        
        # Save HTML file
        output_path = Path(__file__).parent.parent.parent / "annotation_tool.html"
        with open(output_path, "w") as f:
            f.write(html_template)
        
        print(f"✅ Created annotation interface at: {output_path}")
        print(f"📝 Open this file in your browser to annotate {len(selected_cases)} cases")
        print(f"📊 Each case has {len(selected_cases[0]['events']) if selected_cases else 0} events to validate")
        return str(output_path)

if __name__ == "__main__":
    print("🔧 Initializing Ground Truth Annotator...")
    try:
        annotator = GroundTruthAnnotator()
        output_file = annotator.create_annotation_interface(num_cases=10)
        print(f"\n✨ Success! Open this file in your browser:")
        print(f"   file://{output_file}")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you're running this from the correct directory:")
        print("  cd /Users/kanika/Documents/LexIntel/backend")
        print("  python -m research.evaluation.ground_truth")