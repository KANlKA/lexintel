'use client'
// src/app/login/page.tsx
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Scale, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [mode, setMode]         = useState<'login' | 'signup'>('login')
  const router = useRouter()

  async function handleSubmit() {
    if (!email || !password) { setError('Email and password are required.'); return }
    setLoading(true)
    setError(null)

    if (mode === 'login') {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) { setError(error.message); setLoading(false); return }
      router.replace('/')
      router.refresh()
    } else {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) { setError(error.message); setLoading(false); return }
      // After signup, auto-sign in
      const { error: loginErr } = await supabase.auth.signInWithPassword({ email, password })
      if (loginErr) {
        setError('Account created. Please check your email to confirm, then log in.')
        setLoading(false)
        setMode('login')
        return
      }
      router.replace('/')
      router.refresh()
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: '#0A0A0F' }}
    >
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div
            className="w-12 h-12 flex items-center justify-center rounded-lg mb-4"
            style={{ background: 'rgba(201,168,76,0.12)', border: '1px solid rgba(201,168,76,0.3)' }}
          >
            <Scale size={22} style={{ color: '#C9A84C' }} />
          </div>
          <div
            className="text-2xl font-semibold tracking-widest uppercase mb-1"
            style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0', letterSpacing: '0.2em' }}
          >
            LexIntel
          </div>
          <p className="text-xs" style={{ color: '#6B6B80' }}>Legal Intelligence Platform</p>
        </div>

        {/* Card */}
        <div
          className="p-8 rounded-xl"
          style={{ background: '#111118', border: '1px solid #1E1E2A' }}
        >
          {/* Mode toggle */}
          <div className="flex mb-6 rounded-lg overflow-hidden" style={{ border: '1px solid #2A2A38' }}>
            {(['login', 'signup'] as const).map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(null) }}
                className="flex-1 py-2 text-xs uppercase tracking-widest transition-all capitalize"
                style={{
                  fontFamily: 'var(--font-mono)',
                  background: mode === m ? 'rgba(201,168,76,0.1)' : 'transparent',
                  color: mode === m ? '#C9A84C' : '#6B6B80',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                {m === 'login' ? 'Sign In' : 'Sign Up'}
              </button>
            ))}
          </div>

          {/* Fields */}
          <div className="space-y-4 mb-6">
            <div>
              <label className="text-xs uppercase tracking-widest block mb-1.5" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="advocate@chambers.in"
                className="w-full px-4 py-2.5 rounded text-sm outline-none transition-all"
                style={{
                  background: '#0A0A0F',
                  border: '1px solid #2A2A38',
                  color: '#E8E8F0',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={e => (e.target.style.borderColor = 'rgba(201,168,76,0.5)')}
                onBlur={e => (e.target.style.borderColor = '#2A2A38')}
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-widest block mb-1.5" style={{ color: '#6B6B80', fontFamily: 'var(--font-mono)' }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 rounded text-sm outline-none transition-all"
                style={{
                  background: '#0A0A0F',
                  border: '1px solid #2A2A38',
                  color: '#E8E8F0',
                  fontFamily: 'var(--font-body)',
                }}
                onFocus={e => (e.target.style.borderColor = 'rgba(201,168,76,0.5)')}
                onBlur={e => (e.target.style.borderColor = '#2A2A38')}
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <div
              className="flex items-center gap-2 p-3 rounded mb-4 text-xs"
              style={{ background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.2)', color: '#E05252' }}
            >
              <AlertCircle size={13} />
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 rounded text-sm font-medium transition-all"
            style={{
              background: loading ? 'transparent' : 'rgba(201,168,76,0.12)',
              border: '1px solid rgba(201,168,76,0.4)',
              color: loading ? '#6B6B80' : '#C9A84C',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading
              ? '⟳  Please wait…'
              : mode === 'login' ? 'Sign In' : 'Create Account'
            }
          </button>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: '#3A3A4A' }}>
          Your case documents are private and encrypted.
        </p>
      </div>
    </div>
  )
}
