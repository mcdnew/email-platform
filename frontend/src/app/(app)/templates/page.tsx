'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '@/lib/api'
import type { EmailTemplate } from '@/lib/types'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { TiptapEditor } from '@/components/TiptapEditor'
import { Plus, Trash2, Edit2, X, Eye } from 'lucide-react'

const PREVIEW_SAMPLES: Record<string, string> = {
  name: 'Alice', email: 'alice@example.com', company: 'Acme Corp', title: 'CEO',
}

/** Replace {{variable}} tokens with sample values for the live preview. */
function renderPreview(html: string): string {
  return html.replace(/\{\{(\w+)\}\}/g, (_, key) => PREVIEW_SAMPLES[key] ?? `{{${key}}}`)
}

/** Strip HTML tags to produce a plain-text snippet for the card list. */
function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
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
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Templates</h1>
        <button onClick={() => { setShowNew(true); setEditing(null) }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
          <Plus className="w-3.5 h-3.5" /> New template
        </button>
      </div>

      {(showNew || editing) && (
        <TemplateForm
          initial={editing ?? undefined}
          onClose={() => { setShowNew(false); setEditing(null) }}
          onSaved={() => {
            setShowNew(false); setEditing(null)
            qc.invalidateQueries({ queryKey: ['templates'] })
            showToast(editing ? 'Updated' : 'Created')
          }}
          onError={(msg) => showToast(msg, 'err')}
        />
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {templates?.map(t => (
            <div key={t.id} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 text-sm">{t.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{t.subject}</p>
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{stripHtml(t.body)}</p>
                </div>
                <div className="flex gap-1 ml-3">
                  <button onClick={() => setEditing(t)}
                    className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-blue-600 transition-colors">
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => deleteMut.mutate(t.id)}
                    className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-red-600 transition-colors">
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
  const [tab, setTab] = useState<'edit' | 'preview'>('edit')

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
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mb-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{initial ? 'Edit template' : 'New template'}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="w-4 h-4" /></button>
      </div>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Name</label>
          <input required value={form.name} onChange={e => setForm(v => ({ ...v, name: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Subject</label>
          <input required value={form.subject} onChange={e => setForm(v => ({ ...v, subject: e.target.value }))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500" />
        </div>

        {/* Body editor with tab switcher */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Body</label>
            <div className="flex items-center gap-0.5 bg-gray-100 dark:bg-gray-800 rounded-md p-0.5">
              <button
                type="button"
                onClick={() => setTab('edit')}
                className={`flex items-center gap-1 px-2 py-0.5 text-xs rounded transition-colors ${
                  tab === 'edit' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                Edit
              </button>
              <button
                type="button"
                onClick={() => setTab('preview')}
                className={`flex items-center gap-1 px-2 py-0.5 text-xs rounded transition-colors ${
                  tab === 'preview' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm font-medium' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <Eye className="w-3 h-3" /> Preview
              </button>
            </div>
          </div>

          {tab === 'edit' ? (
            <TiptapEditor
              value={form.body}
              onChange={body => setForm(v => ({ ...v, body }))}
              placeholder="Hi {{name}}, …"
            />
          ) : (
            <div
              className="prose-preview min-h-[160px] px-3 py-2 text-sm border border-dashed border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-950 overflow-auto"
              dangerouslySetInnerHTML={{ __html: renderPreview(form.body) || '<span style="color:#9ca3af">Preview will appear here…</span>' }}
            />
          )}
        </div>

        <div className="flex gap-2 pt-1">
          <button type="submit" disabled={loading}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {loading ? 'Saving…' : 'Save'}
          </button>
          <button type="button" onClick={onClose}
            className="px-4 py-1.5 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 text-sm rounded-lg transition-colors dark:text-gray-300">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
