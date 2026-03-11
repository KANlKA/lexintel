'use client'
// src/app/simulation/page.tsx
import { useState, useRef, useEffect } from 'react'
import { getWeaknesses, getContradictions, type Weakness, type Contradiction } from '@/lib/api'
import { Gavel, Send, RotateCcw } from 'lucide-react'

interface Message {
  role: 'judge' | 'opponent' | 'lawyer'
  content: string
  timestamp: string
}

interface SimulationResponse {
  text: string
}

export default function SimulationPage() {
  const [mode, setMode]             = useState<'judge' | 'opponent'>('opponent')
  const [side, setSide]             = useState<'defense' | 'prosecution'>('defense')
  const [messages, setMessages]     = useState<Message[]>([])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [started, setStarted]       = useState(false)
  const [weaknesses, setWeaknesses] = useState<Weakness[]>([])
  const [contradictions, setContradictions] = useState<Contradiction[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getWeaknesses().then(setWeaknesses).catch(() => {})
    getContradictions().then(setContradictions).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function startSimulation() {
    setStarted(true)
    setMessages([])
    setLoading(true)

    try {
      const res = await fetch('/api/simulation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode,
          side,
          weaknesses,
          contradictions,
          messages: [
            { role: 'lawyer', content: 'Begin the hearing. Ask your first question.' },
          ],
        }),
      })
      if (!res.ok) {
        throw new Error('Simulation request failed')
      }
      const data: SimulationResponse = await res.json()
      setMessages([{
        role: mode,
        content: data.text,
        timestamp: new Date().toLocaleTimeString(),
      }])
    } catch {
      setMessages([{ role: mode, content: 'Simulation service is unavailable.', timestamp: new Date().toLocaleTimeString() }])
    } finally {
      setLoading(false)
    }
  }

  async function sendResponse() {
    if (!input.trim() || loading) return

    const userMsg: Message = { role: 'lawyer', content: input, timestamp: new Date().toLocaleTimeString() }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/simulation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode,
          side,
          weaknesses,
          contradictions,
          messages: newMessages,
        }),
      })
      if (!res.ok) {
        throw new Error('Simulation request failed')
      }
      const data: SimulationResponse = await res.json()
      setMessages(prev => [...prev, {
        role: mode,
        content: data.text,
        timestamp: new Date().toLocaleTimeString(),
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: mode,
        content: 'Simulation service is unavailable.',
        timestamp: new Date().toLocaleTimeString(),
      }])
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setStarted(false)
    setMessages([])
    setInput('')
  }

  return (
    <div className="min-h-screen flex flex-col p-8" style={{ background: '#0A0A0F' }}>
      {/* Header */}
      <div className="mb-8 fade-up">
        <div className="text-xs tracking-widest uppercase mb-2" style={{ color: '#C9A84C', fontFamily: 'var(--font-mono)' }}>
          Adversarial Training
        </div>
        <h1 className="text-4xl font-semibold mb-2" style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0' }}>
          Hearing Simulation
        </h1>
        <p style={{ color: '#6B6B80' }}>
          AI simulates a judge or opposing counsel. Respond as a lawyer. Weaknesses and contradictions are loaded automatically.
        </p>
      </div>

      {!started ? (
        /* Setup screen */
        <div className="max-w-lg fade-up">
          <div className="p-6 rounded-lg mb-6" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
            <div className="mb-5">
              <label className="text-xs uppercase tracking-widest block mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                Simulation Mode
              </label>
              <div className="flex gap-2">
                {(['judge', 'opponent'] as const).map(m => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className="flex-1 py-2 rounded text-sm transition-all capitalize"
                    style={{
                      background: mode === m ? 'rgba(201,168,76,0.12)' : 'transparent',
                      border: `1px solid ${mode === m ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
                      color: mode === m ? '#C9A84C' : '#6B6B80',
                      cursor: 'pointer',
                    }}
                  >
                    {m === 'judge' ? '⚖ Judge' : '⚔ Opposing Counsel'}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs uppercase tracking-widest block mb-2" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                Your Role
              </label>
              <div className="flex gap-2">
                {(['defense', 'prosecution'] as const).map(s => (
                  <button
                    key={s}
                    onClick={() => setSide(s)}
                    className="flex-1 py-2 rounded text-sm transition-all capitalize"
                    style={{
                      background: side === s ? 'rgba(201,168,76,0.12)' : 'transparent',
                      border: `1px solid ${side === s ? 'rgba(201,168,76,0.4)' : '#2A2A38'}`,
                      color: side === s ? '#C9A84C' : '#6B6B80',
                      cursor: 'pointer',
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Context summary */}
          {weaknesses.length > 0 && (
            <div className="p-4 rounded-lg mb-6 text-xs space-y-1" style={{ background: '#111118', border: '1px solid #1E1E2A', color: '#6B6B80' }}>
              <div>📋 <span style={{ color: '#A8A8B8' }}>{weaknesses.length}</span> weak events loaded</div>
              <div>⚠️ <span style={{ color: '#A8A8B8' }}>{contradictions.length}</span> contradictions loaded</div>
              <div>🎯 AI will probe these during simulation</div>
            </div>
          )}

          <button
            onClick={startSimulation}
            className="w-full py-3 rounded font-medium transition-all"
            style={{
              background: 'rgba(201,168,76,0.12)',
              border: '1px solid rgba(201,168,76,0.4)',
              color: '#C9A84C',
              cursor: 'pointer',
            }}
          >
            <Gavel size={14} className="inline mr-2" />
            Begin Hearing
          </button>
        </div>
      ) : (
        /* Chat screen */
        <div className="flex flex-col flex-1" style={{ maxHeight: 'calc(100vh - 220px)' }}>
          {/* Messages */}
          <div
            className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2"
            style={{ minHeight: 0 }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'lawyer' ? 'justify-end' : 'justify-start'} fade-up`}
              >
                <div
                  className="max-w-[70%] p-4 rounded-lg"
                  style={
                    msg.role === 'lawyer'
                      ? { background: 'rgba(201,168,76,0.08)', border: '1px solid rgba(201,168,76,0.2)' }
                      : { background: '#111118', border: '1px solid #1E1E2A' }
                  }
                >
                  <div className="text-xs mb-1 flex items-center gap-2" style={{ color: '#6B6B80' }}>
                    <span style={{ color: msg.role === 'lawyer' ? '#C9A84C' : '#E05252' }}>
                      {msg.role === 'lawyer' ? 'You (Lawyer)' : msg.role === 'judge' ? '⚖ Judge' : '⚔ Opposing Counsel'}
                    </span>
                    <span>{msg.timestamp}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: '#E8E8F0', whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="p-4 rounded-lg" style={{ background: '#111118', border: '1px solid #1E1E2A' }}>
                  <div className="flex gap-1">
                    {[0,1,2].map(i => (
                      <div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ background: '#C9A84C', animation: `pulseDot 1.2s ease-in-out ${i * 0.2}s infinite` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex gap-3">
            <button
              onClick={reset}
              className="px-3 py-2 rounded transition-all flex-shrink-0"
              style={{ background: 'transparent', border: '1px solid #2A2A38', color: '#6B6B80', cursor: 'pointer' }}
              title="Reset simulation"
            >
              <RotateCcw size={14} />
            </button>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendResponse()}
              placeholder="Type your response as the lawyer…"
              disabled={loading}
              className="flex-1 px-4 py-2 rounded text-sm outline-none transition-all"
              style={{
                background: '#111118',
                border: '1px solid #2A2A38',
                color: '#E8E8F0',
                fontFamily: 'var(--font-body)',
              }}
            />
            <button
              onClick={sendResponse}
              disabled={loading || !input.trim()}
              className="px-4 py-2 rounded transition-all flex-shrink-0"
              style={{
                background: 'rgba(201,168,76,0.12)',
                border: '1px solid rgba(201,168,76,0.4)',
                color: '#C9A84C',
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                opacity: loading || !input.trim() ? 0.5 : 1,
              }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
