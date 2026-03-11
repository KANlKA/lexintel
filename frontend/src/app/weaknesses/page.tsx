'use client'
// src/app/weaknesses/page.tsx
import { useEffect, useState } from 'react'
import { getWeaknesses, type Weakness } from '@/lib/api'
import { AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'

export default function WeaknessesPage() {
  const [items, setItems]     = useState<Weakness[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [filter, setFilter]   = useState<'all' | 'high' | 'medium' | 'low'>('all')

  useEffect(() => {
    getWeaknesses()
      .then(setItems)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = items.filter(w => filter === 'all' || w.severity === filter)

  return (
    <div className="min-h-screen p-8" style={{ background: '#0A0A0F' }}>
      <div className="mb-8 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#D4882A', fontFamily: 'var(--font-mono)' }}>
          Attack Surface Analysis
        </div>
        <h1 className="text-4xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
          Case Weaknesses
        </h1>
        <p style={{ color: '#6B6B80' }}>
          Events scored by legal vulnerability. Sorted high → low risk.
        </p>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-8">
        {(['all', 'high', 'medium', 'low'] as const).map(f => {
          const colors = { all: '#D4882A', high: '#E05252', medium: '#D4882A', low: '#4CAF7C' }
          const color = colors[f]
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className="px-4 py-1.5 rounded text-xs uppercase tracking-widest transition-all"
              style={{
                fontFamily: 'var(--font-mono)',
                background: filter === f ? `${color}18` : 'transparent',
                border: `1px solid ${filter === f ? `${color}66` : '#2A2A38'}`,
                color: filter === f ? color : '#6B6B80',
                cursor: 'pointer',
              }}
            >
              {f === 'all' ? `All (${items.length})` : `${f} (${items.filter(w => w.severity === f).length})`}
            </button>
          )
        })}
      </div>

      {loading && <LoadingState />}
      {error   && <ErrorState message={error} />}

      {!loading && !error && (
        <div className="space-y-2">
          {filtered.map((w, i) => (
            <WeaknessRow key={w.event_id} weakness={w} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}

function WeaknessRow({ weakness: w, index }: { weakness: Weakness; index: number }) {
  const [open, setOpen] = useState(false)

  const colors = {
    high:   { color: '#E05252', bg: 'rgba(224,82,82,0.06)',  bar: '#E05252' },
    medium: { color: '#D4882A', bg: 'rgba(212,136,42,0.06)', bar: '#D4882A' },
    low:    { color: '#4CAF7C', bg: 'rgba(76,175,124,0.06)', bar: '#4CAF7C' },
  }
  const s = colors[w.severity] || colors.low
  const pct = Math.round(w.weakness_score * 100)

  return (
    <div
      className="rounded-lg overflow-hidden fade-up"
      style={{ animationDelay: `${index * 0.025}s`, background: '#111118', border: '1px solid #1E1E2A' }}
    >
      <div className="px-4 py-3 flex items-center gap-4 cursor-pointer" onClick={() => setOpen(!open)}>
        {/* Score bar */}
        <div className="flex-shrink-0 w-12 text-center">
          <div className="text-lg font-semibold leading-none" style={{ fontFamily: 'var(--font-display)', color: s.color }}>
            {pct}
          </div>
          <div className="text-xs" style={{ color: '#3A3A4A', fontFamily: 'var(--font-mono)' }}>/ 100</div>
        </div>

        {/* Bar */}
        <div className="flex-shrink-0 w-24 h-1.5 rounded-full overflow-hidden" style={{ background: '#1E1E2A' }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: s.bar }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span
              className="text-xs px-2 py-0.5 rounded uppercase tracking-wider flex-shrink-0"
              style={{ background: s.bg, color: s.color, fontFamily: 'var(--font-mono)' }}
            >
              {w.severity}
            </span>
            <span className="text-xs truncate" style={{ color: '#C9A84C' }}>{w.actor}</span>
          </div>
          <p className="text-sm truncate" style={{ color: '#A8A8B8' }}>{w.action}</p>
        </div>

        <div style={{ color: '#6B6B80', flexShrink: 0 }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {open && (
        <div className="px-4 pb-3 pt-0 border-t" style={{ borderColor: '#1E1E2A' }}>
          <div className="mt-3">
            <div className="text-xs uppercase tracking-widest mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
              Risk Factors
            </div>
            <div className="space-y-1">
              {w.reasons.map((r, i) => (
                <div key={i} className="flex items-center gap-2 text-xs" style={{ color: '#A8A8B8' }}>
                  <span style={{ color: s.color }}>·</span>
                  {r}
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs" style={{ color: '#6B6B80' }}>
              Source: <span style={{ color: '#A8A8B8', fontFamily: 'var(--font-mono)' }}>{w.source_document}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex items-center gap-3 py-20 justify-center" style={{ color: '#6B6B80' }}>
      <div className="w-4 h-4 rounded-full border-2 animate-spin" style={{ borderColor: '#D4882A', borderTopColor: 'transparent' }} />
      Loading weakness analysis…
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
