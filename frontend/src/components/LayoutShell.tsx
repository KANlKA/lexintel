'use client'
// src/components/LayoutShell.tsx
// Hides the sidebar on /login and /signup pages.
import { usePathname } from 'next/navigation'
import Sidebar from '@/components/Sidebar'

const NO_SIDEBAR = ['/login', '/signup']

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const path = usePathname()
  const showSidebar = !NO_SIDEBAR.includes(path)

  if (!showSidebar) {
    return <>{children}</>
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="min-h-screen">
        {children}
      </main>
    </div>
  )
}
