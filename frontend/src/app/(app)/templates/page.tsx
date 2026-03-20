'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '@/lib/api'
import type { EmailTemplate } from '@/lib/types'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Plus, Trash2, Edit2, X, Eye } from 'lucide-react'

const PREVIEW_SAMPLES: Record<string, string> = {
  name: 'Alice', email: 'alice@example.com', company: 'Acme Corp', title: 'CEO',
}

function renderPreview(body: string): string {
  return body.replace(/\{\{(\w+)\}\}/g, (_, key) => PREVIEW_SAMPLES[key] ?? `{{${key}}}`)
}

export default function TemplatesPage() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<EmailTemplate | null>(null)
  const [showNew, setShowNew] = useState(false)
  const { toast, showToast } = useToast()

  const { data: templates, isLoading } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })

  const deleteMut = useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); showToast('Deleted') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-gray-900">Templates</h1>
        <button onClick={() => { setShowNew(true); setEditing(null) }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
          <Plus className="w-3.5 h-3.5" /> New template
        </button>
      </div>

      {(showNew || editing) && (
        <TemplateForm
          initial={editing ?? undefined}
          onClose={() => { setShowNew(false); setEditing(null) }}
          onSaved={() => { setShowNew(false); setEditing(null); qc.invalidateQueries({ queryKey: ['templates'] }); showToast(editing ? 'Updated' : 'Created') }}
          onError={(msg) => showToast(msg, 'err')}
        />
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {templates?.map(t => (
            <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900 text-sm">{t.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{t.subject}</p>
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{t.body}</p>
                </div>
                <div className="flex gap-1 ml-3">
                  <button onClick={() => setEditing(t)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 transition-colors">
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => deleteMut.mutate(t.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 transition-colors">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {templates?.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-gray-500 text-sm font-medium">No templates yet</p>
              <p className="text-gray-400 text-xs mt-1">Create your first template to start sending emails.</p>
            </div>
          )}
        </div>
      )}

      <Toast toast={toast} />
    </div>
  )
}

function TemplateForm({ initial, onClose, onSaved, onError }: {
  initial?: EmailTemplate
  onClose: () => void
  onSaved: () => void
  onError: (msg: string) => void
}) {
  const [form, setForm] = useState({
    name: initial?.name ?? '',
    subject: initial?.subject ?? '',
    body: initial?.body ?? '',
  })
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      if (initial) await updateTemplate(initial.id, form)
      else await createTemplate(form)
      onSaved()
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-900">{initial ? 'Edit template' : 'New template'}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="w-4 h-4" /></button>
      </div>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input required value={form.name} onChange={e => setForm(v => ({ ...v, name: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
          <input required value={form.subject} onChange={e => setForm(v => ({ ...v, subject: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Body</label>
            <textarea required rows={8} value={form.body} onChange={e => setForm(v => ({ ...v, body: e.target.value }))}
              placeholder="Hi {{name}}, ..."
              aria-label="Template body"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-none" />
          </div>
          <div>
            <div className="flex items-center gap-1 mb-1">
              <Eye className="w-3 h-3 text-gray-400" />
              <label className="text-xs font-medium text-gray-600">Live preview</label>
            </div>
            <div className="h-[calc(8*1.5rem+1rem)] px-3 py-2 text-sm border border-dashed border-gray-300 rounded-lg bg-gray-50 overflow-auto whitespace-pre-wrap text-gray-700">
              {renderPreview(form.body) || <span className="text-gray-400">Preview will appear here…</span>}
            </div>
          </div>
        </div>
        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={loading}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {loading ? 'Saving…' : 'Save'}
          </button>
          <button type="button" onClick={onClose}
            className="px-4 py-1.5 bg-white hover:bg-gray-50 border border-gray-300 text-sm rounded-lg transition-colors">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
