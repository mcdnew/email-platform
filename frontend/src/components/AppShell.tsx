'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  LayoutDashboard, Users, FileText, GitBranch,
  Clock, Mail, Settings, LogOut, Send,
} from 'lucide-react'
import { clsx } from 'clsx'

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/prospects', label: 'Prospects', icon: Users },
  { href: '/templates', label: 'Templates', icon: FileText },
  { href: '/sequences', label: 'Sequences', icon: GitBranch },
  { href: '/queue', label: 'Queue', icon: Clock },
  { href: '/sent', label: 'Sent', icon: Mail },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  async function logout() {
    await fetch('/api/auth', { method: 'DELETE' })
    router.push('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Send className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-gray-900 text-sm">Email Platform</span>
          </div>
        </div>
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                pathname === href
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="p-2 border-t border-gray-200">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
