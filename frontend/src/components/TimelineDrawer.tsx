'use client'

import { useQuery } from '@tanstack/react-query'
import { getProspectTimeline } from '@/lib/api'
import type { Prospect } from '@/lib/types'
import { X } from 'lucide-react'
import { StatusBadge } from './StatusBadge'

const fmt = (d: string | null) =>
  d ? new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'

export function TimelineDrawer({ prospect, onClose }: { prospect: Prospect; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ['timeline', prospect.id],
    queryFn: () => getProspectTimeline(prospect.id),
  })

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-full max-w-md bg-white dark:bg-gray-900 shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{prospect.name}</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{prospect.email}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {/* Sequence label */}
        {prospect.sequence_name && (
          <div className="px-5 py-2.5 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-100 dark:border-blue-800">
            <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">Sequence: {prospect.sequence_name}</span>
          </div>
        )}

        {/* Timeline */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading ? (
            <p className="text-sm text-gray-400 text-center py-8">Loading…</p>
          ) : !data?.length ? (
            <div className="text-center py-12">
              <p className="text-sm text-gray-500 font-medium">No emails scheduled</p>
              <p className="text-xs text-gray-400 mt-1">Assign a sequence to this prospect to get started.</p>
            </div>
          ) : (
            <ol className="relative border-l border-gray-200 dark:border-gray-700 ml-3 space-y-6">
              {data.map((entry, i) => (
                <li key={i} className="ml-5">
                  <span className={`absolute -left-2.5 flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ring-2 ring-white dark:ring-gray-900
                    ${entry.status === 'opened' ? 'bg-green-500 text-white' :
                      entry.status === 'sent' ? 'bg-blue-500 text-white' :
                      entry.status === 'failed' ? 'bg-red-500 text-white' :
                      entry.status === 'sending' ? 'bg-yellow-500 text-white' :
                      'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}`}>
                    {entry.step_number ?? i + 1}
                  </span>
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div>
                        <p className="text-xs font-semibold text-gray-900 dark:text-gray-100">{entry.template_name}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate max-w-xs">{entry.subject}</p>
                      </div>
                      <StatusBadge status={entry.status} />
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
                      <div>
                        <p className="text-xs text-gray-400">Scheduled</p>
                        <p className="text-xs text-gray-600 dark:text-gray-300">{fmt(entry.scheduled_at)}</p>
                      </div>
                      {entry.sent_at && (
                        <div>
                          <p className="text-xs text-gray-400">Sent</p>
                          <p className="text-xs text-gray-600 dark:text-gray-300">{fmt(entry.sent_at)}</p>
                        </div>
                      )}
                      {entry.opened_at && (
                        <div>
                          <p className="text-xs text-gray-400">Opened</p>
                          <p className="text-xs text-green-600 dark:text-green-400 font-medium">{fmt(entry.opened_at)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </>
  )
}
