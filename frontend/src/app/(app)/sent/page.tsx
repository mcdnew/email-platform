'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getSentEmails } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { PaginationBar } from '@/components/PaginationBar'

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
        <h1 className="text-xl font-semibold text-gray-900">Sent History</h1>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">All statuses</option>
          <option value="sent">Sent</option>
          <option value="opened">Opened</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['To', 'Subject', 'Template', 'Sequence', 'Sent At', 'Status'].map(h => (
                <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
            ) : !data?.items.length ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400 text-sm">No emails found.</td></tr>
            ) : data.items.map(e => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-3 py-2.5 font-medium text-gray-900 text-xs">{e.to}</td>
                <td className="px-3 py-2.5 text-gray-600 max-w-xs truncate text-xs">{e.subject}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{e.template_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{e.sequence_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-400 text-xs">{new Date(e.sent_at).toLocaleString()}</td>
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
