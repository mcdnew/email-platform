'use client'

import { useQuery } from '@tanstack/react-query'
import { getAnalytics, getAnalyticsByTemplate, getAnalyticsBySequence } from '@/lib/api'
import type { BreakdownRow } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, Mail, XCircle, Eye } from 'lucide-react'

const STAT_COLORS: Record<string, string> = {
  blue: 'text-blue-500',
  green: 'text-emerald-500',
  red: 'text-red-400',
  purple: 'text-violet-500',
}

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ['analytics'], queryFn: getAnalytics })
  const { data: byTemplate } = useQuery({ queryKey: ['analytics-by-template'], queryFn: getAnalyticsByTemplate })
  const { data: bySequence } = useQuery({ queryKey: ['analytics-by-sequence'], queryFn: getAnalyticsBySequence })

  if (isLoading) return <PageShell title="Dashboard"><div className="text-gray-500 text-sm">Loading…</div></PageShell>
  if (error || !data) return <PageShell title="Dashboard"><div className="text-red-500 text-sm">Failed to load analytics.</div></PageShell>

  const chartData = [
    { name: 'Sent', value: data.total_sent - data.total_failed },
    { name: 'Failed', value: data.total_failed },
    { name: 'Opened', value: Math.round(data.open_rate * data.total_sent / 100) },
  ]

  return (
    <PageShell title="Dashboard">
      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Mail} label="Total Sent" value={data.total_sent} color="blue" />
        <StatCard icon={TrendingUp} label="Open Rate" value={`${data.open_rate}%`} color="green" />
        <StatCard icon={XCircle} label="Failed" value={data.total_failed} color="red" />
        <StatCard icon={Eye} label="Sent Today" value={data.sent_today} color="purple" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Chart */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Email Status Overview</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Recent activity */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Recent Emails</h2>
          <div className="space-y-2">
            {data.recent.length === 0 && <p className="text-sm text-gray-400">No emails sent yet.</p>}
            {data.recent.map((e, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="truncate flex-1 mr-2">
                  <span className="font-medium text-gray-900 dark:text-gray-100">{e.to}</span>
                  <span className="text-gray-400 ml-1">— {e.subject}</span>
                </div>
                <StatusBadge status={e.status} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Breakdowns */}
      {((byTemplate && byTemplate.length > 0) || (bySequence && bySequence.length > 0)) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          {byTemplate && byTemplate.length > 0 && <BreakdownTable title="By Template" rows={byTemplate} />}
          {bySequence && bySequence.length > 0 && <BreakdownTable title="By Sequence" rows={bySequence} />}
        </div>
      )}
    </PageShell>
  )
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ElementType; label: string; value: string | number; color: string
}) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 flex items-start gap-3">
      <Icon className={`w-4 h-4 mt-1 flex-shrink-0 ${STAT_COLORS[color]}`} />
      <div>
        <div className="text-2xl font-bold text-gray-900 dark:text-gray-100 tabular-nums">{value}</div>
        <div className="text-xs text-gray-500 mt-0.5">{label}</div>
      </div>
    </div>
  )
}

function BreakdownTable({ title, rows }: { title: string; rows: BreakdownRow[] }) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{title}</h2>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-100 dark:border-gray-800">
            <th className="pb-2 font-medium">Name</th>
            <th className="pb-2 font-medium text-right">Sent</th>
            <th className="pb-2 font-medium text-right">Opened</th>
            <th className="pb-2 font-medium text-right">Open %</th>
            <th className="pb-2 font-medium text-right">Failed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
          {rows.map(r => (
            <tr key={r.id}>
              <td className="py-1.5 text-gray-700 dark:text-gray-300 truncate max-w-[140px]">{r.name}</td>
              <td className="py-1.5 text-right text-gray-600 dark:text-gray-400">{r.sent}</td>
              <td className="py-1.5 text-right text-green-600 dark:text-green-400">{r.opened}</td>
              <td className="py-1.5 text-right font-medium text-gray-900 dark:text-gray-100">{r.open_rate}%</td>
              <td className="py-1.5 text-right text-red-500">{r.failed}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PageShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-5">{title}</h1>
      {children}
    </div>
  )
}
