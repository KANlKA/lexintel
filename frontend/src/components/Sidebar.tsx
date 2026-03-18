'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Scale,
  Clock,
  AlertTriangle,
  Shield,
  Gavel,
  Activity,
  FolderOpen,
  LogOut,
} from 'lucide-react'
import clsx from 'clsx'
import { supabase, signOut } from '@/lib/supabase'
import type { User } from '@supabase/supabase-js'

const nav = [
  { href: '/', label: 'Dashboard', icon: Activity },
  { href: '/workspace', label: 'Case Workspace', icon: FolderOpen },
]

export default function Sidebar() {
  const path = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user))

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [])

  async function handleSignOut() {
    await signOut()
    router.push('/login')
  }

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : '??'

  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{
        background: 'rgba(13,13,20,0.94)',
        borderColor: '#1E1E2A',
        backdropFilter: 'blur(14px)',
      }}
    >
      <div className="flex items-center justify-between gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-3.5">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-md"
            style={{
              background: 'rgba(201,168,76,0.12)',
              border: '1px solid rgba(201,168,76,0.3)',
            }}
          >
            <Scale size={20} style={{ color: '#C9A84C' }} />
          </div>
          <div>
            <div
              className="text-lg font-semibold uppercase tracking-widest"
              style={{
                fontFamily: 'var(--font-display)',
                color: '#E8E8F0',
                letterSpacing: '0.18em',
              }}
            >
              LexIntel
            </div>
            <div className="text-sm" style={{ color: '#6B6B80' }}>
              Legal Intelligence
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          <nav className="flex items-center gap-2">
            {nav.map(({ href, label, icon: Icon }) => {
              const active = path === href

              return (
                <Link
                  key={href}
                  href={href}
                  className={clsx(
                    'flex items-center gap-2 rounded-full px-4 py-2 text-sm transition-all duration-200',
                    active
                      ? 'text-[#C9A84C]'
                      : 'text-[#6B6B80] hover:bg-[#16161F] hover:text-[#A8A8B8]',
                  )}
                  style={
                    active
                      ? {
                          background: 'rgba(201,168,76,0.08)',
                          border: '1px solid rgba(201,168,76,0.28)',
                        }
                      : {
                          border: '1px solid transparent',
                        }
                  }
                >
                  <Icon size={14} />
                  <span>{label}</span>
                  {href === '/workspace' && !active && (
                    <span
                      className="rounded px-1.5 py-0.5 text-xs"
                      style={{
                        background: 'rgba(201,168,76,0.1)',
                        color: '#C9A84C',
                        fontSize: '10px',
                      }}
                    >
                      START
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          {user ? (
            <div className="flex items-center gap-3">
              <div
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-medium"
                style={{
                  background: 'rgba(201,168,76,0.15)',
                  color: '#C9A84C',
                  border: '1px solid rgba(201,168,76,0.3)',
                }}
              >
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs" style={{ color: '#A8A8B8' }}>
                  {user.email}
                </div>
                <div className="text-xs" style={{ color: '#3A3A4A' }}>
                  Signed in
                </div>
              </div>
              <button
                onClick={handleSignOut}
                title="Sign out"
                className="flex-shrink-0 rounded p-1.5 transition-all"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#6B6B80',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = '#E05252')}
                onMouseLeave={e => (e.currentTarget.style.color = '#6B6B80')}
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <div className="text-xs" style={{ color: '#3A3A4A' }}>
              Not signed in
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
