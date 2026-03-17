'use client'
// src/components/Sidebar.tsx
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Scale, Clock, AlertTriangle, Shield, Gavel, Activity, FolderOpen } from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { href: '/workspace',      label: 'Case Workspace', icon: FolderOpen }
]

export default function Sidebar() {
  const path = usePathname()

  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{
        background: 'rgba(13,13,20,0.92)',
        borderColor: '#1E1E2A',
        backdropFilter: 'blur(14px)',
      }}
    >
      <div className="flex items-center justify-between gap-6 px-6 py-4">
        <Link href="/workspace" className="flex items-center gap-3">
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
        </Link>

        <nav className="flex flex-wrap items-center justify-end gap-2">
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
                    : 'text-[#6B6B80] hover:text-[#A8A8B8] hover:bg-[#16161F]',
                )}
                style={active ? {
                  background: 'rgba(201,168,76,0.08)',
                  border: '1px solid rgba(201,168,76,0.28)',
                } : {
                  border: '1px solid transparent',
                }}
              >
                <Icon size={14} />
                <span>{label}</span>
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
