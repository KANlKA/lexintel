'use client'
// src/app/timeline/page.tsx
import { useEffect, useState, type ReactNode } from 'react'
import { getTimeline, type TimelineEvent } from '@/lib/api'
import { Clock, MapPin, User, FileText, AlertCircle } from 'lucide-react'

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'timed' | 'uncertain'>('all')

  useEffect(() => {
    getTimeline()
      .then(setEvents)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = events.filter(e => {
    if (filter === 'timed')     return !e.time_uncertain
    if (filter === 'uncertain') return e.time_uncertain
    return true
  })

  return (
    <div className="min-h-screen p-8" style={{ background: '#0A0A0F' }}>
      {/* Header */}
      <div className="mb-8 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
          Case Reconstruction
        </div>
        <h1 className="text-4xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
          Event Timeline
        </h1>
        <p style={{ color: '#6B6B80' }}>
          Chronological sequence of all extracted case events.
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-8">
        {(['all', 'timed', 'uncertain'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-4 py-1.5 rounded text-xs uppercase tracking-widest transition-all"
            style={{
              fontFamily: 'var(--font-mono)',
              background: filter === f ? 'rgba(201,168,76,0.12)' : 'transparent',
              border: `1px solid ${filter === f ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
              color: filter === f ? '#C9A84C' : '#6B6B80',
              cursor: 'pointer',
            }}
          >
            {f === 'all' ? `All (${events.length})` : f === 'timed' ? `Timed (${events.filter(e => !e.time_uncertain).length})` : `Uncertain (${events.filter(e => e.time_uncertain).length})`}
          </button>
        ))}
      </div>

      {loading && <LoadingState />}
      {error   && <ErrorState message={error} />}

      {!loading && !error && (
        <div className="relative">
          {/* Vertical line */}
          <div
            className="absolute left-[19px] top-0 bottom-0 w-px"
            style={{ background: 'linear-gradient(to bottom, #C9A84C, #2A2A38 80%)' }}
          />

          <div className="space-y-1">
            {filtered.map((event, i) => (
              <TimelineNode key={event.event_id} event={event} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TimelineNode({ event, index }: { event: TimelineEvent; index: number }) {
  const [open, setOpen] = useState(false)
  const conf = event.confidence
  const confColor = conf >= 0.8 ? '#4CAF7C' : conf >= 0.7 ? '#D4882A' : '#E05252'

  return (
    <div
      className="relative pl-10 fade-up"
      style={{ animationDelay: `${index * 0.03}s` }}
    >
      {/* Node dot */}
      <div
        className="absolute left-[13px] top-4 w-3 h-3 rounded-full border-2 z-10"
        style={{
          background: event.time_uncertain ? '#1E1E2A' : '#C9A84C',
          borderColor: event.time_uncertain ? '#3A3A4A' : '#C9A84C',
          boxShadow: event.time_uncertain ? 'none' : '0 0 8px rgba(201,168,76,0.4)',
        }}
      />

      <div
        className="mb-1 rounded-lg overflow-hidden transition-all duration-200 cursor-pointer hover:border-[#3A3A4A]"
        style={{ background: '#111118', border: '1px solid #1E1E2A' }}
        onClick={() => setOpen(!open)}
      >
        <div className="px-4 py-3 flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(107,143,212,0.15)', color: '#6B8FD4', fontFamily: 'var(--font-mono)' }}>
                #{event.timeline_position}
              </span>
              {event.time_uncertain && (
                <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(107,107,128,0.15)', color: '#6B6B80' }}>
                  time uncertain
                </span>
              )}
              <span className="text-xs" style={{ color: confColor, fontFamily: 'var(--font-mono)' }}>
                {Math.round(conf * 100)}% conf
              </span>
            </div>
            <div className="text-sm font-medium" style={{ color: '#E8E8F0' }}>
              <span style={{ color: '#C9A84C' }}>{event.actor}</span>
              <span style={{ color: '#6B6B80' }}> → </span>
              {event.action}
            </div>
          </div>
          <div className="text-xs text-right flex-shrink-0" style={{ color: '#6B6B80' }}>
            {event.time || '—'}
          </div>
        </div>

        {/* Expanded detail */}
        {open && (
          <div className="px-4 pb-3 pt-0 border-t" style={{ borderColor: '#1E1E2A' }}>
            <div className="grid grid-cols-2 gap-3 mt-3">
              {event.location && (
                <DetailRow icon={<MapPin size={12} />} label="Location" value={event.location} />
              )}
              <DetailRow icon={<FileText size={12} />} label="Source" value={event.source_document} />
              {event.time && (
                <DetailRow icon={<Clock size={12} />} label="Time" value={event.time} />
              )}
              <DetailRow icon={<User size={12} />} label="Actor" value={event.actor} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function DetailRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5" style={{ color: '#6B6B80' }}>{icon}</span>
      <div>
        <div className="text-xs uppercase tracking-wider mb-0.5" style={{ color: '#3A3A4A', fontFamily: 'var(--font-mono)' }}>{label}</div>
        <div className="text-xs" style={{ color: '#A8A8B8' }}>{value}</div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center gap-3 py-20 justify-center" style={{ color: '#6B6B80' }}>
      <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: '#C9A84C', borderTopColor: 'transparent' }} />
      Loading timeline…
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 p-6 rounded-lg" style={{ background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.2)' }}>
      <AlertCircle size={16} style={{ color: '#E05252' }} />
      <span className="text-sm" style={{ color: '#E05252' }}>{message} — Run POST /analyze first.</span>
    </div>
  )
}
