// src/lib/api.ts

export interface Event {
  event_id: string
  actor: string
  action: string
  time: string | null
  location: string | null
  source_document: string
  confidence: number
}

export interface TimelineEvent extends Event {
  timeline_position: number
  time_uncertain: boolean
  parsed_hour: number | null
}

export interface Contradiction {
  event1_id: string
  event2_id: string
  type: string
  description: string
  severity: 'critical' | 'moderate' | 'minor'
  event1_summary: string
  event2_summary: string
}

export interface Weakness {
  event_id: string
  actor: string
  action: string
  weakness_score: number
  severity: 'high' | 'medium' | 'low'
  reasons: string[]
  source_document: string
}

export interface Summary {
  events_total: number
  timed_events: number
  uncertain_events: number
  contradictions_total: number
  critical_contradictions: number
  high_weakness_events: number
  medium_weakness_events: number
  low_weakness_events: number
  graph: { nodes: number; edges: number }
}

export interface AnalyzeResponse {
  status: string
  events_extracted: number
  timeline_events: number
  contradictions_found: number
  weaknesses_scored: number
  graph: { nodes: number; edges: number }
}

export interface CaseProcessResponse {
  status: string
  events_extracted: number
  events: Event[]
}

// ── Case workspace storage (in-memory, survives page navigation) ─────────────

export interface CaseWorkspace {
  id: string
  name: string
  files: string[]
  createdAt: string
  analyzed: boolean
  eventCount: number
  lastAnalyzedAt?: string
}

export interface WorkspaceAnalysis {
  summary: Summary
  timeline: TimelineEvent[]
  contradictions: Contradiction[]
  weaknesses: Weakness[]
  updatedAt: string
}

const WORKSPACES_KEY = 'lexintel_workspaces'
const WORKSPACE_ANALYSIS_KEY = 'lexintel_workspace_analysis'

export function getWorkspaces(): CaseWorkspace[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(WORKSPACES_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveWorkspace(ws: CaseWorkspace): void {
  const all = getWorkspaces().filter(w => w.id !== ws.id)
  localStorage.setItem(WORKSPACES_KEY, JSON.stringify([ws, ...all]))
}

export function deleteWorkspace(id: string): void {
  const all = getWorkspaces().filter(w => w.id !== id)
  localStorage.setItem(WORKSPACES_KEY, JSON.stringify(all))

  const analysisMap = getWorkspaceAnalysisMap()
  delete analysisMap[id]
  localStorage.setItem(WORKSPACE_ANALYSIS_KEY, JSON.stringify(analysisMap))
}

function getWorkspaceAnalysisMap(): Record<string, WorkspaceAnalysis> {
  if (typeof window === 'undefined') return {}
  try {
    return JSON.parse(localStorage.getItem(WORKSPACE_ANALYSIS_KEY) || '{}')
  } catch {
    return {}
  }
}

export function getWorkspaceAnalysis(id: string): WorkspaceAnalysis | null {
  const analysisMap = getWorkspaceAnalysisMap()
  return analysisMap[id] ?? null
}

export function saveWorkspaceAnalysis(id: string, analysis: WorkspaceAnalysis): void {
  const analysisMap = getWorkspaceAnalysisMap()
  analysisMap[id] = analysis
  localStorage.setItem(WORKSPACE_ANALYSIS_KEY, JSON.stringify(analysisMap))
}

// ── API helpers ───────────────────────────────────────────────────────────────

const REASONING = '/api/reasoning'
const PIPELINE = '/api/pipeline'

async function get<T>(base: string, path: string): Promise<T> {
  const res = await fetch(`${base}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `API error ${res.status}`)
  }
  return res.json()
}

// Dataset analysis (existing flow)
export async function analyze(datasetPath: string, limit: number): Promise<AnalyzeResponse> {
  const res = await fetch(`${REASONING}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_path: datasetPath, limit }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Analyze failed ${res.status}`)
  }
  return res.json()
}

// ── Case workspace flow ───────────────────────────────────────────────────────

/**
 * Step 1: Upload files to pipeline -> get events back
 */
export async function uploadCaseFiles(files: File[]): Promise<CaseProcessResponse> {
  const form = new FormData()
  files.forEach(f => form.append('files', f))

  const res = await fetch(`${PIPELINE}/process/case`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Upload failed ${res.status}`)
  }
  return res.json()
}

/**
 * Step 2: Send extracted events to reasoning engine -> get full analysis
 */
export async function analyzeEvents(events: Event[]): Promise<AnalyzeResponse> {
  const res = await fetch(`${REASONING}/analyze/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(events),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Analysis failed ${res.status}`)
  }
  return res.json()
}

// GET endpoints (same for both dataset and case workspace flows)
export const getEvents = () => get<Event[]>(REASONING, '/events')
export const getTimeline = () => get<TimelineEvent[]>(REASONING, '/timeline')
export const getContradictions = () => get<Contradiction[]>(REASONING, '/contradictions')
export const getWeaknesses = () => get<Weakness[]>(REASONING, '/weaknesses')
export const getSummary = () => get<Summary>(REASONING, '/summary')
export const getHealth = () => get<{ status: string }>(REASONING, '/health')
