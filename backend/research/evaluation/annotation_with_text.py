"""Ground Truth Annotation Tool WITH Original Document Text"""
import json
from pathlib import Path
import random

class AnnotatorWithText:
    def __init__(self):
        base = Path(__file__).parent.parent.parent
        self.events_path = base / "../dataset/extracted_events.json"
        self.raw_data_path = base / "../dataset/text.data.jsonl"
        
        print(f"📂 Loading events from: {self.events_path}")
        print(f"📂 Loading raw text from: {self.raw_data_path}")
        
        with open(self.events_path) as f:
            self.data = json.load(f)
        
        # Load raw case texts
        self.raw_cases = {}
        with open(self.raw_data_path) as f:
            for line in f:
                if line.strip():
                    case = json.loads(line)
                    # Try to find case ID - adjust based on your format
                    case_id = case.get('id', case.get('case_id', case.get('doc_id', '')))
                    if case_id:
                        self.raw_cases[case_id] = case.get('text', case.get('content', ''))
        
        print(f"✅ Loaded {len(self.raw_cases)} raw case documents")
        
        # Extract events by case
        self.cases = []
        for case_id, events in self.data.get('by_case', {}).items():
            case_events = []
            for event in events:
                extracted_event = {
                    'event_id': event.get('event_id', ''),
                    'actor': event.get('actor', 'Unknown'),
                    'action': event.get('action', 'Unknown'),
                    'time': event.get('time', 'Unknown'),
                    'location': event.get('location', 'Unknown'),
                    'confidence': event.get('confidence', 0)
                }
                case_events.append(extracted_event)
            
            # Get original document text
            original_text = self.raw_cases.get(case_id, "Original text not available")
            
            self.cases.append({
                'case_id': case_id,
                'events': case_events,
                'num_events': len(case_events),
                'original_text': original_text[:3000]  # Limit length
            })
        
        print(f"📊 Found {len(self.cases)} cases with {sum(c['num_events'] for c in self.cases)} total events")
    
    def create_annotation_tool(self, num_cases: int = 3):
        """Create HTML annotation interface with document text"""
        
        sample_cases = random.sample(self.cases, min(num_cases, len(self.cases)))
        
        cases_data = []
        for case in sample_cases:
            cases_data.append({
                'id': case['case_id'],
                'events': case['events'],
                'num_events': case['num_events'],
                'original_text': case['original_text']
            })
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>LexIntel Ground Truth Annotation</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
        h1 { color: #2c3e50; }
        .instructions { background: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #3498db; }
        .stats-bar { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .case { background: white; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .case-header { background: #2c3e50; color: white; padding: 15px; border-radius: 8px 8px 0 0; cursor: pointer; }
        .case-header:hover { background: #34495e; }
        .case-content { padding: 20px; display: none; }
        .case-content.active { display: block; }
        .original-text { background: #fef9e7; padding: 15px; margin-bottom: 20px; border-left: 4px solid #f39c12; border-radius: 4px; font-family: monospace; font-size: 14px; line-height: 1.6; max-height: 400px; overflow-y: auto; }
        .original-text h4 { margin-top: 0; color: #e67e22; }
        .events-section { margin-top: 20px; }
        .event { background: #f8f9fa; margin: 15px 0; padding: 15px; border-left: 4px solid #3498db; border-radius: 4px; }
        .event.correct { border-left-color: #27ae60; background: #e8f5e9; }
        .event.incorrect { border-left-color: #e74c3c; background: #fdecea; }
        .event-field { display: inline-block; margin: 5px 8px; padding: 4px 10px; background: white; border-radius: 4px; font-size: 14px; }
        .event-field strong { color: #2c3e50; }
        .guidelines { background: #e8f4f8; padding: 10px; margin: 10px 0; border-radius: 4px; font-size: 13px; }
        button { margin: 5px; padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; font-size: 13px; }
        .btn-correct { background: #27ae60; color: white; }
        .btn-correct:hover { background: #229954; }
        .btn-incorrect { background: #e74c3c; color: white; }
        .btn-incorrect:hover { background: #c0392b; }
        .btn-save { background: #3498db; color: white; padding: 12px 24px; font-size: 16px; margin-top: 20px; }
        .btn-save:hover { background: #2980b9; }
        .annotation-status { font-size: 12px; margin-top: 8px; color: #7f8c8d; }
        .toggle-icon { float: right; font-size: 20px; }
        .confidence { font-size: 11px; color: #7f8c8d; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>📝 LexIntel Ground Truth Annotation</h1>
    
    <div class="instructions">
        <strong>📖 How to Judge Correct/Incorrect:</strong>
        <ul>
            <li><strong>✓ CORRECT</strong> = The extracted information matches what's in the original document text</li>
            <li><strong>✗ INCORRECT</strong> = The extraction is wrong, missing, or hallucinated</li>
        </ul>
        <strong>Example:</strong> If document says "defendant ran away at 10 PM" and event shows actor="defendant", action="ran away", time="10 PM" → ✓ CORRECT<br>
        If document says one thing but event shows something else → ✗ INCORRECT
    </div>
    
    <div class="stats-bar" id="stats">Loading...</div>
    
    <div id="cases-container"></div>
    
    <div style="text-align: center;">
        <button class="btn-save" onclick="saveAllAnnotations()">💾 Download Ground Truth (JSON)</button>
    </div>

    <script>
        const casesData = """ + json.dumps(cases_data) + """;
        let annotations = {};
        
        function calculateStats() {
            let totalAnnotated = Object.keys(annotations).length;
            let totalCorrect = Object.values(annotations).filter(v => v === true).length;
            let totalEvents = 0;
            for (let case_ of casesData) {
                totalEvents += case_.events.length;
            }
            let percentComplete = totalEvents > 0 ? (totalAnnotated / totalEvents * 100).toFixed(1) : 0;
            let precision = totalAnnotated > 0 ? (totalCorrect / totalAnnotated * 100).toFixed(1) : 0;
            
            document.getElementById('stats').innerHTML = `
                <strong>📊 Progress:</strong> ${totalAnnotated}/${totalEvents} events annotated (${percentComplete}%)<br>
                <strong>✅ Correct:</strong> ${totalCorrect} &nbsp;|&nbsp;
                <strong>❌ Incorrect:</strong> ${totalAnnotated - totalCorrect} &nbsp;|&nbsp;
                <strong>📈 Current Precision:</strong> ${precision}%
            `;
        }
        
        function toggleCase(caseId) {
            const content = document.getElementById(`case-content-${caseId}`);
            content.classList.toggle('active');
            const icon = document.getElementById(`toggle-icon-${caseId}`);
            if (content.classList.contains('active')) {
                icon.textContent = '▼';
            } else {
                icon.textContent = '▶';
            }
        }
        
        function annotateEvent(caseId, eventIdx, isCorrect) {
            const key = `${caseId}_${eventIdx}`;
            annotations[key] = isCorrect;
            
            const eventDiv = document.getElementById(`event-${caseId}-${eventIdx}`);
            if (isCorrect) {
                eventDiv.classList.add('correct');
                eventDiv.classList.remove('incorrect');
            } else {
                eventDiv.classList.add('incorrect');
                eventDiv.classList.remove('correct');
            }
            
            const statusSpan = document.getElementById(`status-${caseId}-${eventIdx}`);
            if (isCorrect) {
                statusSpan.innerHTML = '✓ Marked as correct';
            } else {
                statusSpan.innerHTML = '✗ Marked as incorrect';
            }
            
            calculateStats();
        }
        
        function renderCases() {
            let html = '';
            
            for (let case_ of casesData) {
                // Truncate text if too long
                let displayText = case_.original_text;
                if (displayText.length > 2000) {
                    displayText = displayText.substring(0, 2000) + '...';
                }
                
                html += `
                    <div class="case">
                        <div class="case-header" onclick="toggleCase('${case_.id}')">
                            <strong>📁 Case ID: ${case_.id}</strong>
                            <span class="toggle-icon" id="toggle-icon-${case_.id}">▶</span>
                            <div style="font-size: 12px; margin-top: 5px;">${case_.events.length} events to annotate</div>
                        </div>
                        <div class="case-content" id="case-content-${case_.id}">
                            <div class="original-text">
                                <h4>📄 Original Document Text (Reference):</h4>
                                <div>${displayText.replace(/\\n/g, '<br>')}</div>
                            </div>
                            <div class="events-section">
                                <h3>🎯 Extracted Events (Judge each against the text above):</h3>
                `;
                
                for (let i = 0; i < case_.events.length; i++) {
                    const event = case_.events[i];
                    const key = `${case_.id}_${i}`;
                    const isAnnotated = annotations[key] !== undefined;
                    const isCorrect = annotations[key] === true;
                    let statusClass = '';
                    if (isAnnotated) {
                        statusClass = isCorrect ? 'correct' : 'incorrect';
                    }
                    
                    html += `
                        <div class="event ${statusClass}" id="event-${case_.id}-${i}">
                            <div><strong>Event ${i + 1}:</strong></div>
                            <div class="event-field"><strong>👤 Actor:</strong> ${event.actor}</div>
                            <div class="event-field"><strong>⚡ Action:</strong> ${event.action}</div>
                            <div class="event-field"><strong>⏰ Time:</strong> ${event.time}</div>
                            <div class="event-field"><strong>📍 Location:</strong> ${event.location}</div>
                            <div class="confidence"><strong>🤖 LLM Confidence:</strong> ${(event.confidence * 100).toFixed(1)}%</div>
                            <div>
                                <button class="btn-correct" onclick="annotateEvent('${case_.id}', ${i}, true)">✓ Correct - Matches document</button>
                                <button class="btn-incorrect" onclick="annotateEvent('${case_.id}', ${i}, false)">✗ Incorrect - Doesn't match document</button>
                            </div>
                            <div class="annotation-status" id="status-${case_.id}-${i}">
                    `;
                    
                    if (isAnnotated) {
                        if (isCorrect) {
                            html += '✓ Marked as correct (matches document)';
                        } else {
                            html += '✗ Marked as incorrect (does not match document)';
                        }
                    } else {
                        html += '⏳ Not yet judged - compare with document text above';
                    }
                    
                    html += `
                            </div>
                        </div>
                    `;
                }
                
                html += `</div></div></div>`;
            }
            
            document.getElementById('cases-container').innerHTML = html;
            calculateStats();
        }
        
        function saveAllAnnotations() {
            const results = {
                timestamp: new Date().toISOString(),
                total_cases: casesData.length,
                cases: []
            };
            
            for (let case_ of casesData) {
                const caseAnnotations = {
                    case_id: case_.id,
                    total_events: case_.events.length,
                    annotated_events: [],
                    correct_events: [],
                    incorrect_events: []
                };
                
                for (let i = 0; i < case_.events.length; i++) {
                    const key = `${case_.id}_${i}`;
                    if (annotations[key] !== undefined) {
                        const event = case_.events[i];
                        const isCorrect = annotations[key];
                        caseAnnotations.annotated_events.push({
                            event: event,
                            is_correct: isCorrect
                        });
                        if (isCorrect) {
                            caseAnnotations.correct_events.push(event);
                        } else {
                            caseAnnotations.incorrect_events.push(event);
                        }
                    }
                }
                
                caseAnnotations.num_annotated = caseAnnotations.annotated_events.length;
                if (caseAnnotations.num_annotated > 0) {
                    caseAnnotations.precision = (caseAnnotations.correct_events.length / caseAnnotations.num_annotated * 100).toFixed(1);
                } else {
                    caseAnnotations.precision = 0;
                }
                
                results.cases.push(caseAnnotations);
            }
            
            const totalAnnotated = results.cases.reduce((sum, c) => sum + c.num_annotated, 0);
            const totalCorrect = results.cases.reduce((sum, c) => sum + c.correct_events.length, 0);
            if (totalAnnotated > 0) {
                results.overall_precision = (totalCorrect / totalAnnotated * 100).toFixed(1);
            } else {
                results.overall_precision = 0;
            }
            results.total_annotated = totalAnnotated;
            results.total_correct = totalCorrect;
            
            const blob = new Blob([JSON.stringify(results, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ground_truth_${new Date().toISOString().slice(0,19)}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            alert(`✅ Ground truth saved!\\n📊 Annotated: ${totalAnnotated} events\\n✅ Correct: ${totalCorrect}\\n📈 Precision: ${results.overall_precision}%`);
        }
        
        renderCases();
    </script>
</body>
</html>"""
        
        output_path = Path(__file__).parent.parent.parent / "annotation_tool_with_text.html"
        with open(output_path, "w") as f:
            f.write(html)
        
        print(f"\n✅ Created annotation tool with document text: {output_path}")
        print(f"\n📊 Annotating: {len(sample_cases)} cases with {sum(len(c['events']) for c in sample_cases)} events")
        print(f"\n🌐 Open this file in your browser:")
        print(f"   file://{output_path}")
        
        return output_path

if __name__ == "__main__":
    print("🔧 Starting Annotation Tool with Document Text...")
    print("=" * 50)
    annotator = AnnotatorWithText()
    annotator.create_annotation_tool(num_cases=3)
    print("\n✨ Ready! Open the HTML file to start annotating.")
    print("\n📖 How to judge:")
    print("   - Read the ORIGINAL DOCUMENT TEXT")
    print("   - Compare with each extracted event")
    print("   - Click CORRECT if the event matches the document")
    print("   - Click INCORRECT if the event doesn't match")
