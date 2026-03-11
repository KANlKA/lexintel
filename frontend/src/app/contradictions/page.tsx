'use client'
// src/app/contradictions/page.tsx
import { useEffect, useState } from 'react'
import { getContradictions, type Contradiction } from '@/lib/api'
import { AlertTriangle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'

export default function ContradictionsPage() {
  const [items, setItems]   = useState<Contradiction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'critical' | 'moderate'>('all')

  useEffect(() => {
    getContradictions()
      .then(setItems)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = items.filter(c => filter === 'all' || c.severity === filter)
  const critical = items.filter(c => c.severity === 'critical').length
  const moderate = items.filter(c => c.severity === 'moderate').length

  return (
    <div className="min-h-screen p-8" style={{ background: '#0A0A0F' }}>
      {/* Header */}
      <div className="mb-8 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#E05252', fontFamily: 'var(--font-mono)' }}>
          Conflict Detection
        </div>
        <h1 className="text-4xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
          Contradictions
        </h1>
        <p style={{ color: '#6B6B80' }}>
          Logical conflicts and inconsistencies detected across case documents.
        </p>
      </div>

      {/* Summary bar */}
      {!loading && !error && (
        <div className="flex gap-4 mb-8 fade-up">
          <SeverityBadge count={critical} label="Critical" color="#E05252" bg="rgba(224,82,82,0.1)" />
          <SeverityBadge count={moderate} label="Moderate" color="#D4882A" bg="rgba(212,136,42,0.1)" />
          <SeverityBadge count={items.length - critical - moderate} label="Minor" color="#4CAF7C" bg="rgba(76,175,124,0.1)" />
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 mb-6">
        {(['all', 'critical', 'moderate'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-4 py-1.5 rounded text-xs uppercase tracking-widest transition-all"
            style={{
              fontFamily: 'var(--font-mono)',
              background: filter === f ? 'rgba(224,82,82,0.1)' : 'transparent',
              border: `1px solid ${filter === f ? 'rgba(224,82,82,0.4)' : '#2A2A38'}`,
              color: filter === f ? '#E05252' : '#6B6B80',
              cursor: 'pointer',
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {loading && <LoadingState />}
      {error   && <ErrorState message={error} />}

      {!loading && !error && filtered.length === 0 && (
        <div className="py-20 text-center" style={{ color: '#6B6B80' }}>
          No contradictions found in this filter.
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map((c, i) => (
            <ContradictionCard key={`${c.event1_id}-${c.event2_id}`} contradiction={c} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}

function ContradictionCard({ contradiction: c, index }: { contradiction: Contradiction; index: number }) {
  const [open, setOpen] = useState(false)

  const severityStyles: Record<string, { color: string; bg: string; border: string }> = {
    critical: { color: '#E05252', bg: 'rgba(224,82,82,0.06)',  border: 'rgba(224,82,82,0.25)' },
    moderate: { color: '#D4882A', bg: 'rgba(212,136,42,0.06)', border: 'rgba(212,136,42,0.25)' },
    minor:    { color: '#4CAF7C', bg: 'rgba(76,175,124,0.06)', border: 'rgba(76,175,124,0.25)' },
  }
  const s = severityStyles[c.severity] || severityStyles.minor

  return (
    <div
      className="rounded-lg overflow-hidden fade-up"
      style={{ animationDelay: `${index * 0.04}s`, background: s.bg, border: `1px solid ${s.border}` }}
    >
      <div
        className="px-5 py-4 flex items-start justify-between cursor-pointer"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-start gap-3 flex-1">
          <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" style={{ color: s.color }} />
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className="text-xs px-2 py-0.5 rounded uppercase tracking-wider"
                style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}`, fontFamily: 'var(--font-mono)' }}
              >
                {c.severity}
              </span>
              <span className="text-xs" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                {c.type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-sm" style={{ color: '#A8A8B8' }}>{c.description}</p>
          </div>
        </div>
        <div style={{ color: '#6B6B80' }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && (
        <div className="px-5 pb-4 pt-0 border-t" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="p-3 rounded" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1E1E2A' }}>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>Event 1</div>
              <p className="text-xs" style={{ color: '#A8A8B8' }}>{c.event1_summary}</p>
            </div>
            <div className="p-3 rounded" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1E1E2A' }}>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>Event 2</div>
              <p className="text-xs" style={{ color: '#A8A8B8' }}>{c.event2_summary}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SeverityBadge({ count, label, color, bg }: { count: number; label: string; color: string; bg: string }) {
  return (
    <div className="px-4 py-2 rounded-lg flex items-center gap-2" style={{ background: bg, border: `1px solid ${color}30` }}>
      <span className="text-lg font-semibold" style={{ fontFamily: 'var(--font-display)', color }}>{count}</span>
      <span className="text-xs" style={{ color }}>{label}</span>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center gap-3 py-20 justify-center" style={{ color: '#6B6B80' }}>
      <div className="w-4 h-4 rounded-full border-2 animate-spin" style={{ borderColor: '#E05252', borderTopColor: 'transparent' }} />
      Loading contradictions…
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
