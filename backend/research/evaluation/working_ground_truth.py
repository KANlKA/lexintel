"""Ground Truth Annotation Tool - Works with your exact JSON structure"""
import json
from pathlib import Path
import random

class WorkingAnnotator:
    def __init__(self):
        base = Path(__file__).parent.parent.parent
        self.events_path = base / "../dataset/extracted_events.json"
        
        print(f"📂 Loading from: {self.events_path}")
        
        with open(self.events_path) as f:
            self.data = json.load(f)
        
        print(f"✅ Loaded: {self.data.get('total_cases', 0)} cases with {self.data.get('total_events', 0)} total events")
        
        # Extract events by case
        self.cases = []
        self.all_events = []
        
        for case_id, events in self.data.get('by_case', {}).items():
            case_events = []
            for event in events:
                # Extract relevant fields
                extracted_event = {
                    'event_id': event.get('event_id', ''),
                    'actor': event.get('actor', 'Unknown'),
                    'action': event.get('action', 'Unknown'),
                    'time': event.get('time', 'Unknown'),
                    'location': event.get('location', 'Unknown'),
                    'confidence': event.get('confidence', 0)
                }
                case_events.append(extracted_event)
                self.all_events.append(extracted_event)
            
            self.cases.append({
                'case_id': case_id,
                'events': case_events,
                'num_events': len(case_events)
            })
        
        print(f"📊 Found {len(self.cases)} cases with events")
        print(f"📊 Total events: {len(self.all_events)}")
    
    def create_annotation_tool(self, num_cases: int = 5):
        """Create HTML annotation interface"""
        
        # Select sample cases
        sample_cases = random.sample(self.cases, min(num_cases, len(self.cases)))
        
        # Prepare data for HTML
        cases_data = []
        for case in sample_cases:
            cases_data.append({
                'id': case['case_id'],
                'events': case['events'],
                'num_events': case['num_events']
            })
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>LexIntel Ground Truth Annotation</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
        h1 { color: #2c3e50; }
        .stats-bar { background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .case { background: white; margin: 20px 0; padding: 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .case-header { background: #2c3e50; color: white; padding: 15px; border-radius: 8px 8px 0 0; cursor: pointer; }
        .case-header:hover { background: #34495e; }
        .case-content { padding: 20px; display: none; }
        .case-content.active { display: block; }
        .event { background: #f8f9fa; margin: 10px 0; padding: 15px; border-left: 4px solid #3498db; border-radius: 4px; }
        .event.correct { border-left-color: #27ae60; background: #e8f5e9; }
        .event.incorrect { border-left-color: #e74c3c; background: #fdecea; }
        .event-field { display: inline-block; margin: 5px 8px; padding: 4px 10px; background: white; border-radius: 4px; font-size: 14px; }
        .event-field strong { color: #2c3e50; }
        button { margin: 5px; padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; font-size: 13px; }
        .btn-correct { background: #27ae60; color: white; }
        .btn-correct:hover { background: #229954; }
        .btn-incorrect { background: #e74c3c; color: white; }
        .btn-incorrect:hover { background: #c0392b; }
        .btn-save { background: #3498db; color: white; padding: 12px 24px; font-size: 16px; margin-top: 20px; }
        .btn-save:hover { background: #2980b9; }
        .progress { background: #ecf0f1; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .confidence { font-size: 11px; color: #7f8c8d; margin-top: 5px; }
        .annotation-status { font-size: 12px; margin-top: 8px; color: #7f8c8d; }
        .toggle-icon { float: right; font-size: 20px; }
    </style>
</head>
<body>
    <h1>📝 LexIntel Ground Truth Annotation</h1>
    <p>For each extracted event, mark if it is <strong>correct</strong> based on the original legal document.</p>
    
    <div class="stats-bar" id="stats">
        Loading...
    </div>
    
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
            let percentComplete = (totalAnnotated / totalEvents * 100).toFixed(1);
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
                html += `
                    <div class="case">
                        <div class="case-header" onclick="toggleCase('${case_.id}')">
                            <strong>📁 Case ID: ${case_.id}</strong>
                            <span class="toggle-icon" id="toggle-icon-${case_.id}">▶</span>
                            <div style="font-size: 12px; margin-top: 5px;">${case_.events.length} events</div>
                        </div>
                        <div class="case-content" id="case-content-${case_.id}">
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
                            <div class="confidence"><strong>Confidence:</strong> ${(event.confidence * 100).toFixed(1)}%</div>
                            <div>
                                <button class="btn-correct" onclick="annotateEvent('${case_.id}', ${i}, true)">✓ Correct</button>
                                <button class="btn-incorrect" onclick="annotateEvent('${case_.id}', ${i}, false)">✗ Incorrect</button>
                            </div>
                            <div class="annotation-status" id="status-${case_.id}-${i}">
                    `;
                    
                    if (isAnnotated) {
                        if (isCorrect) {
                            html += '✓ Marked as correct';
                        } else {
                            html += '✗ Marked as incorrect';
                        }
                    } else {
                        html += 'Not annotated yet';
                    }
                    
                    html += `
                            </div>
                        </div>
                    `;
                }
                
                html += `</div></div>`;
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
        
        output_path = Path(__file__).parent.parent.parent / "annotation_tool.html"
        with open(output_path, "w") as f:
            f.write(html)
        
        print(f"\n✅ Created annotation tool: {output_path}")
        print(f"\n📊 What's in your data:")
        print(f"   - Total cases: {len(self.cases)}")
        print(f"   - Total events: {len(self.all_events)}")
        print(f"   - Annotating: {len(sample_cases)} cases with {sum(len(c['events']) for c in sample_cases)} events")
        
        print(f"\n🌐 Open this file in your browser:")
        print(f"   file://{output_path}")
        
        print(f"\n📝 Instructions:")
        print(f"   1. Click on each case to expand it")
        print(f"   2. For each event, click ✓ Correct or ✗ Incorrect")
        print(f"   3. Download the ground truth JSON when done")
        
        return output_path

if __name__ == "__main__":
    print("🔧 Starting Ground Truth Annotation Tool...")
    print("=" * 50)
    annotator = WorkingAnnotator()
    annotator.create_annotation_tool(num_cases=5)
    print("\n✨ Ready! Open the HTML file in your browser to start annotating.")
