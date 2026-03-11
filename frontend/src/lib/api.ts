// src/lib/api.ts
// All API calls go through Next.js rewrites → localhost:8000

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

const BASE = '/api/reasoning'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `API error ${res.status}`)
  }
  return res.json()
}

export async function analyze(datasetPath: string, limit: number): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
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

export const getEvents        = ()  => get<Event[]>('/events')
export const getTimeline      = ()  => get<TimelineEvent[]>('/timeline')
export const getContradictions = () => get<Contradiction[]>('/contradictions')
export const getWeaknesses    = ()  => get<Weakness[]>('/weaknesses')
export const getSummary       = ()  => get<Summary>('/summary')
export const getHealth        = ()  => get<{ status: string }>('/health')
