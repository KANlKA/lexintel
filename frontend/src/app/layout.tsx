// src/app/layout.tsx
import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata: Metadata = {
  title: 'LexIntel — Legal Intelligence Platform',
  description: 'AI-powered litigation intelligence and hearing preparation',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <Sidebar />
          <main className="min-h-[calc(100vh-73px)]">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
