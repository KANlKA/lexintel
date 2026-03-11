'use client'
// src/app/page.tsx — Case Dashboard
import { useState, useEffect, type ReactNode } from 'react'
import { analyze, getSummary, type Summary } from '@/lib/api'
import { AlertTriangle, Clock, Shield, Zap, Database, GitBranch } from 'lucide-react'
import Link from 'next/link'

export default function Dashboard() {
  const [summary, setSummary]   = useState<Summary | null>(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [analyzed, setAnalyzed] = useState(false)

  // Try loading existing summary on mount
  useEffect(() => {
    getSummary()
      .then(s => { setSummary(s); setAnalyzed(true) })
      .catch(() => {})
  }, [])

  async function runAnalysis() {
    setLoading(true)
    setError(null)
    try {
      await analyze('../dataset/text.data.jsonl', 10)
      const s = await getSummary()
      setSummary(s)
      setAnalyzed(true)
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-8" style={{ background: '#0A0A0F' }}>
      {/* Header */}
      <div className="mb-10 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
          Case Intelligence Platform
        </div>
        <h1
          className="text-4xl font-semibold mb-2"
          style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0', lineHeight: 1.2 }}
        >
          Case Dashboard
        </h1>
        <p style={{ color: '#6B6B80' }}>
          AI-powered litigation intelligence. Extract events, detect contradictions, prepare for hearings.
        </p>
      </div>

      {/* Analyze button */}
      {!analyzed && (
        <div
          className="mb-10 p-8 rounded-lg text-center fade-up"
          style={{ border: '1px dashed #2A2A38', background: '#111118' }}
        >
          <div className="text-2xl mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
            No case analyzed yet
          </div>
          <p className="text-sm mb-6" style={{ color: '#6B6B80' }}>
            Run the pipeline to extract events, build a timeline, and detect contradictions.
          </p>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-6 py-3 rounded text-sm font-medium transition-all duration-200"
            style={{
              background: loading ? '#2A2A38' : 'rgba(201,168,76,0.15)',
              border: '1px solid rgba(201,168,76,0.4)',
              color: loading ? '#6B6B80' : '#C9A84C',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? '⟳  Analyzing case documents…' : '⚡  Analyze Case Dataset'}
          </button>
          {error && <p className="mt-4 text-sm" style={{ color: '#E05252' }}>{error}</p>}
        </div>
      )}

      {/* Stats grid */}
      {summary && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-8 fade-up">
            <StatCard
              icon={<Database size={18} />}
              label="Total Events"
              value={summary.events_total}
              sub={`${summary.timed_events} timed · ${summary.uncertain_events} uncertain`}
              accent="#C9A84C"
            />
            <StatCard
              icon={<AlertTriangle size={18} />}
              label="Contradictions"
              value={summary.contradictions_total}
              sub={`${summary.critical_contradictions} critical`}
              accent="#E05252"
            />
            <StatCard
              icon={<Shield size={18} />}
              label="High Risk Events"
              value={summary.high_weakness_events}
              sub={`${summary.medium_weakness_events} medium · ${summary.low_weakness_events} low`}
              accent="#D4882A"
            />
            <StatCard
              icon={<GitBranch size={18} />}
              label="Event Graph"
              value={summary.graph?.nodes ?? 0}
              sub={`${summary.graph?.edges ?? 0} relationships`}
              accent="#4CAF7C"
            />
            <StatCard
              icon={<Clock size={18} />}
              label="Timeline Events"
              value={summary.timed_events}
              sub="chronologically ordered"
              accent="#6B8FD4"
            />
            <StatCard
              icon={<Zap size={18} />}
              label="Coverage"
              value={`${summary.events_total > 0 ? Math.round((summary.timed_events / summary.events_total) * 100) : 0}%`}
              sub="events with known time"
              accent="#A084D4"
            />
          </div>

          {/* Quick links */}
          <div className="grid grid-cols-2 gap-4 fade-up">
            <QuickLink href="/timeline"       title="View Timeline"        desc="Chronological sequence of all case events" color="#6B8FD4" />
            <QuickLink href="/contradictions" title="Contradictions"       desc={`${summary.critical_contradictions} critical conflicts detected`} color="#E05252" />
            <QuickLink href="/weaknesses"     title="Weakness Analysis"    desc={`${summary.high_weakness_events} high-risk events identified`} color="#D4882A" />
            <QuickLink href="/simulation"     title="Hearing Simulation"   desc="Prepare for adversarial questioning" color="#C9A84C" />
          </div>

          {/* Re-analyze */}
          <div className="mt-8">
            <button
              onClick={runAnalysis}
              disabled={loading}
              className="text-xs px-4 py-2 rounded transition-all"
              style={{
                background: 'transparent',
                border: '1px solid #2A2A38',
                color: '#6B6B80',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? '⟳  Re-analyzing…' : '↻  Re-run Analysis'}
            </button>
            {error && <span className="ml-4 text-xs" style={{ color: '#E05252' }}>{error}</span>}
          </div>
        </>
      )}
    </div>
  )
}

function StatCard({
  icon, label, value, sub, accent,
}: {
  icon: ReactNode
  label: string
  value: number | string
  sub: string
  accent: string
}) {
  return (
    <div
      className="p-5 rounded-lg transition-all duration-200 hover:translate-y-[-2px]"
      style={{ background: '#111118', border: '1px solid #1E1E2A' }}
    >
      <div className="flex items-center gap-2 mb-3" style={{ color: accent }}>
        {icon}
        <span className="text-xs uppercase tracking-widest" style={{ fontFamily: 'var(--font-mono)', color: '#6B6B80' }}>
          {label}
        </span>
      </div>
      <div className="text-3xl font-semibold mb-1" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
        {value}
      </div>
      <div className="text-xs" style={{ color: '#6B6B80' }}>{sub}</div>
    </div>
  )
}

function QuickLink({ href, title, desc, color }: { href: string; title: string; desc: string; color: string }) {
  return (
    <Link
      href={href}
      className="block p-5 rounded-lg transition-all duration-200 hover:translate-y-[-2px]"
      style={{ background: '#111118', border: '1px solid #1E1E2A' }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium" style={{ color: '#E8E8F0' }}>{title}</span>
        <span style={{ color }}>→</span>
      </div>
      <p className="text-xs" style={{ color: '#6B6B80' }}>{desc}</p>
    </Link>
  )
}
