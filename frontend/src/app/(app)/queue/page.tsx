'use client'

import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getQueue, deleteQueueItem } from '@/lib/api'
import { StatusBadge } from '@/components/StatusBadge'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Trash2 } from 'lucide-react'

export default function QueuePage() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const { toast, showToast } = useToast()

  const { data: queue, isLoading } = useQuery({ queryKey: ['queue'], queryFn: getQueue, refetchInterval: 30_000 })

  const deleteMut = useMutation({
    mutationFn: deleteQueueItem,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['queue'] }); showToast('Removed from queue') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const filtered = useMemo(
    () => statusFilter ? queue?.filter(e => e.status === statusFilter) : queue,
    [queue, statusFilter],
  )

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Scheduled Queue</h1>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="sending">Sending</option>
          <option value="sent">Sent</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <tr>
              {['Prospect', 'Email', 'Template', 'Send At', 'Status', ''].map(h => (
                <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
            ) : !filtered?.length ? (
              <tr><td colSpan={6} className="px-3 py-12 text-center">
                <p className="text-gray-500 text-sm font-medium">Queue is empty</p>
                <p className="text-gray-400 text-xs mt-1">Assign a sequence to prospects to schedule emails.</p>
              </td></tr>
            ) : filtered.map(e => (
              <tr key={e.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="px-3 py-2.5 font-medium text-gray-900 dark:text-gray-100">{e.prospect_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{e.prospect_email ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400">{e.template_name ?? '—'}</td>
                <td className="px-3 py-2.5 text-gray-500 text-xs">{new Date(e.send_at).toLocaleString()}</td>
                <td className="px-3 py-2.5"><StatusBadge status={e.status} /></td>
                <td className="px-3 py-2.5">
                  {e.status === 'pending' && (
                    <button onClick={() => deleteMut.mutate(e.id)}
                      className="p-1 text-gray-300 hover:text-red-500 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Toast toast={toast} />
    </div>
  )
}
