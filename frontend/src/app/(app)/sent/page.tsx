'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getSentEmails } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { PaginationBar } from '@/components/PaginationBar'
import { downloadCsv } from '@/lib/csv'
import { Download } from 'lucide-react'

export default function SentPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['sent', page, statusFilter],
    queryFn: () => getSentEmails({ page, per_page: 50, sort_by: 'sent_at', order: 'desc', status_filter: statusFilter }),
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Sent History</h1>
        <div className="flex items-center gap-2">
        <button
          onClick={() => downloadCsv(
            (data?.items ?? []).map(e => ({ to: e.to, subject: e.subject, template: e.template_name ?? '', sequence: e.sequence_name ?? '', sent_at: e.sent_at, status: e.status })),
            'sent-history.csv'
          )}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors">
          <Download className="w-3.5 h-3.5" />
          Export CSV
        </button>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
          <option value="">All statuses</option>
          <option value="sent">Sent</option>
          <option value="opened">Opened</option>
          <option value="failed">Failed</option>
          <option value="bounced">Bounced</option>
        </select>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <tr>
              {['To', 'Subject', 'Template', 'Sequence', 'Sent At', 'Clicks', 'Status'].map(h => (
                <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
            ) : !data?.items.length ? (
              <tr><td colSpan={7} className="px-3 py-12 text-center">
                <p className="text-gray-500 text-sm font-medium">No emails yet</p>
                <p className="text-gray-400 text-xs mt-1">Sent emails will appear here once the scheduler runs.</p>
              </td></tr>
            ) : data.items.map(e => (
              <tr key={e.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="px-3 py-2.5 font-medium text-gray-900 dark:text-gray-100 text-xs">{e.to}</td>
                <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400 max-w-xs truncate text-xs">{e.subject}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{e.template_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{e.sequence_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-400 text-xs">{new Date(e.sent_at).toLocaleString()}</td>
                <td className="px-3 py-2.5 text-xs text-gray-500">{e.click_count > 0 ? e.click_count : '—'}</td>
                <td className="px-3 py-2.5"><StatusBadge status={e.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>

        {data && data.pages > 1 && (
          <PaginationBar
            total={data.total}
            page={data.page}
            pages={data.pages}
            label="emails"
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  )
}
