'use client'

import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getQueue, deleteQueueItem, patchQueueItem, getTemplates } from '@/lib/api'
import type { ScheduledEmail } from '@/lib/types'
import { StatusBadge } from '@/components/StatusBadge'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Trash2, Pencil } from 'lucide-react'

export default function QueuePage() {
  const qc = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [editItem, setEditItem] = useState<ScheduledEmail | null>(null)
  const { toast, showToast } = useToast()

  const { data: queue, isLoading } = useQuery({ queryKey: ['queue'], queryFn: getQueue, refetchInterval: 30_000 })

  const deleteMut = useMutation({
    mutationFn: deleteQueueItem,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['queue'] }); showToast('Removed from queue') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const patchMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { send_at?: string; template_id?: number } }) =>
      patchQueueItem(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['queue'] }); setEditItem(null); showToast('Updated') },
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
                    <div className="flex items-center gap-1">
                      <button onClick={() => setEditItem(e)}
                        className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-300 hover:text-blue-500 transition-colors" title="Reschedule">
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => deleteMut.mutate(e.id)}
                        className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-300 hover:text-red-500 transition-colors" title="Remove">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editItem && (
        <EditModal
          item={editItem}
          onClose={() => setEditItem(null)}
          onSave={(data) => patchMut.mutate({ id: editItem.id, data })}
          saving={patchMut.isPending}
        />
      )}

      <Toast toast={toast} />
    </div>
  )
}

function EditModal({ item, onClose, onSave, saving }: {
  item: ScheduledEmail
  onClose: () => void
  onSave: (data: { send_at?: string; template_id?: number }) => void
  saving: boolean
}) {
  const { data: templates } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })

  // Convert UTC ISO string to local datetime-local input value
  const toLocalInput = (iso: string) => {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  const [sendAt, setSendAt] = useState(toLocalInput(item.send_at))
  const [templateId, setTemplateId] = useState<number>(item.template_id ?? 0)

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const data: { send_at?: string; template_id?: number } = {}
    const newIso = new Date(sendAt).toISOString()
    if (newIso !== new Date(item.send_at).toISOString()) data.send_at = newIso
    if (templateId && templateId !== item.template_id) data.template_id = templateId
    if (Object.keys(data).length === 0) { onClose(); return }
    onSave(data)
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <form onSubmit={submit} className="bg-white dark:bg-gray-900 rounded-xl shadow-xl p-6 w-96 border border-gray-200 dark:border-gray-700">
        <h3 className="text-sm font-semibold mb-4 dark:text-gray-100">Edit scheduled email</h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          {item.prospect_name} · {item.prospect_email}
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Send at</label>
            <input type="datetime-local" value={sendAt} onChange={e => setSendAt(e.target.value)} required
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Template</label>
            <select value={templateId} onChange={e => setTemplateId(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
              {templates?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button type="submit" disabled={saving}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            Save
          </button>
          <button type="button" onClick={onClose}
            className="py-2 px-4 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 text-sm rounded-lg transition-colors dark:text-gray-300">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
