import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import './globals.css'
import LayoutShell from '@/components/LayoutShell'

export const metadata: Metadata = {
  title: 'LexIntel — Legal Intelligence Platform',
  description: 'AI-powered litigation intelligence and hearing preparation',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  )
}
