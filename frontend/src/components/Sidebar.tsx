'use client'
// src/components/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Scale, Clock, AlertTriangle, Shield, Gavel, Activity } from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { href: '/',               label: 'Dashboard',    icon: Activity },
  { href: '/timeline',       label: 'Timeline',     icon: Clock },
  { href: '/contradictions', label: 'Contradictions', icon: AlertTriangle },
  { href: '/weaknesses',     label: 'Weaknesses',   icon: Shield },
  { href: '/simulation',     label: 'Simulation',   icon: Gavel },
]

export default function Sidebar() {
  const path = usePathname()

  return (
    <aside
      className="fixed top-0 left-0 h-screen w-60 flex flex-col z-50"
      style={{ background: '#0D0D14', borderRight: '1px solid #1E1E2A' }}
    >
      {/* Logo */}
      <div className="px-6 py-7" style={{ borderBottom: '1px solid #1E1E2A' }}>
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 flex items-center justify-center rounded"
            style={{ background: 'rgba(201,168,76,0.12)', border: '1px solid rgba(201,168,76,0.3)' }}
          >
            <Scale size={16} style={{ color: '#C9A84C' }} />
          </div>
          <div>
            <div
              className="text-sm font-semibold tracking-widest uppercase"
              style={{ fontFamily: 'var(--font-display)', color: '#E8E8F0', letterSpacing: '0.15em' }}
            >
              LexIntel
            </div>
            <div className="text-xs" style={{ color: '#6B6B80' }}>Legal Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all duration-200',
                active
                  ? 'text-[#E8E8F0]'
                  : 'text-[#6B6B80] hover:text-[#A8A8B8] hover:bg-[#16161F]'
              )}
              style={active ? {
                background: 'rgba(201,168,76,0.08)',
                borderLeft: '2px solid #C9A84C',
                color: '#C9A84C',
              } : {}}
            >
              <Icon size={15} />
              <span>{label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4" style={{ borderTop: '1px solid #1E1E2A' }}>
        <div className="text-xs" style={{ color: '#3A3A4A' }}>
          v1.0.0 · Academic Build
        </div>
      </div>
    </aside>
  )
}
