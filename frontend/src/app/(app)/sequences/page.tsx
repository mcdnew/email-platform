'use client'

import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors, DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates,
  useSortable, verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  getSequences, createSequence, deleteSequence,
  getSteps, createStep, deleteStep, reorderSteps, getTemplates,
} from '@/lib/api'
import type { EmailTemplate, SequenceStep } from '@/lib/types'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Plus, Trash2, GripVertical, ChevronRight } from 'lucide-react'

export default function SequencesPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<number | null>(null)
  const [showNew, setShowNew] = useState(false)
  const { toast, showToast } = useToast()

  const { data: sequences } = useQuery({ queryKey: ['sequences'], queryFn: getSequences })
  const { data: steps } = useQuery({
    queryKey: ['steps', selected],
    queryFn: () => getSteps(selected!),
    enabled: !!selected,
  })
  const { data: templates } = useQuery({ queryKey: ['templates'], queryFn: getTemplates })

  // O(1) template name lookup — avoids O(n×m) Array.find during drag renders
  const templateNameById = useMemo(
    () => new Map(templates?.map(t => [t.id, t.name])),
    [templates],
  )

  const seq = sequences?.find(s => s.id === selected)

  const delSeqMut = useMutation({
    mutationFn: deleteSequence,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['sequences'] }); setSelected(null); showToast('Deleted') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const delStepMut = useMutation({
    mutationFn: deleteStep,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['steps', selected] }); showToast('Step removed') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const reorderMut = useMutation({
    mutationFn: ({ sid, steps }: { sid: number; steps: Array<{ step_id: number; delay_days: number }> }) =>
      reorderSteps(sid, steps),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['steps', selected] }) },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id || !steps || !selected) return

    const oldIdx = steps.findIndex(s => s.id === active.id)
    const newIdx = steps.findIndex(s => s.id === over.id)
    const reordered = arrayMove(steps, oldIdx, newIdx).map((s, i) => ({
      ...s, delay_days: i,
    }))

    qc.setQueryData(['steps', selected], reordered)
    reorderMut.mutate({ sid: selected, steps: reordered.map(s => ({ step_id: s.id, delay_days: s.delay_days })) })
  }

  return (
    <div className="p-6 flex gap-6">
      {/* Sequence list */}
      <div className="w-64 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Sequences</h1>
          <button onClick={() => setShowNew(true)}
            className="p-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors">
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {showNew && (
          <NewSeqForm
            onClose={() => setShowNew(false)}
            onSaved={(id) => { setShowNew(false); setSelected(id); qc.invalidateQueries({ queryKey: ['sequences'] }); showToast('Created') }}
            onError={(msg) => showToast(msg, 'err')}
          />
        )}

        <div className="space-y-1">
          {sequences?.map(s => (
            <button key={s.id} onClick={() => setSelected(s.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${selected === s.id ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'}`}>
              <span className="font-medium truncate">{s.name}</span>
              <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />
            </button>
          ))}
          {!sequences?.length && (
            <div className="px-3 py-4 text-center">
              <p className="text-xs font-medium text-gray-500">No sequences yet</p>
              <p className="text-xs text-gray-400 mt-0.5 dark:text-gray-600">Press + to create one.</p>
            </div>
          )}
        </div>
      </div>

      {/* Steps panel */}
      {selected && seq && (
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{seq.name}</h2>
              {seq.bcc_email && <p className="text-xs text-gray-400">BCC: {seq.bcc_email}</p>}
            </div>
            <button onClick={() => delSeqMut.mutate(selected)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 border border-red-200 rounded-lg transition-colors">
              <Trash2 className="w-3.5 h-3.5" /> Delete sequence
            </button>
          </div>

          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Steps (drag to reorder)</h3>
            {steps && steps.length > 0 ? (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                  {steps.map((step, idx) => (
                    <SortableStep
                      key={step.id}
                      step={step}
                      index={idx}
                      templateName={templateNameById.get(step.template_id) ?? `Template #${step.template_id}`}
                      onDelete={() => delStepMut.mutate(step.id)}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            ) : (
              <p className="text-sm text-gray-400 py-2">No steps yet. Add one below.</p>
            )}
          </div>

          <AddStepForm
            sequenceId={selected}
            templates={templates ?? []}
            onSaved={() => { qc.invalidateQueries({ queryKey: ['steps', selected] }); showToast('Step added') }}
            onError={(msg) => showToast(msg, 'err')}
          />
        </div>
      )}

      <Toast toast={toast} />
    </div>
  )
}

function SortableStep({ step, index, templateName, onDelete }: {
  step: SequenceStep; index: number; templateName: string; onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div ref={setNodeRef} style={style} className="flex items-center gap-3 py-2.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <button {...attributes} {...listeners} className="text-gray-300 hover:text-gray-500 dark:hover:text-gray-400 cursor-grab active:cursor-grabbing">
        <GripVertical className="w-4 h-4" />
      </button>
      <div className="flex-1 flex items-center gap-3">
        <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold flex items-center justify-center">
          {index + 1}
        </span>
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{templateName}</div>
          <div className="text-xs text-gray-400">Day {step.delay_days}</div>
        </div>
      </div>
      <button onClick={onDelete} className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-300 hover:text-red-500 transition-colors">
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

function AddStepForm({ sequenceId, templates, onSaved, onError }: {
  sequenceId: number
  templates: EmailTemplate[]
  onSaved: () => void
  onError: (msg: string) => void
}) {
  const [templateId, setTemplateId] = useState<number | ''>('')
  const [delay, setDelay] = useState(0)
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!templateId) return
    setLoading(true)
    try {
      await createStep(sequenceId, { template_id: Number(templateId), delay_days: delay })
      onSaved()
      setTemplateId('')
      setDelay(0)
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Add step</h3>
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-xs text-gray-500 mb-1">Template</label>
          <select required value={templateId} onChange={e => setTemplateId(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100">
            <option value="">Select template…</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
        <div className="w-28">
          <label className="block text-xs text-gray-500 mb-1">Send on day</label>
          <input type="number" min={0} value={delay} onChange={e => setDelay(Number(e.target.value))}
            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100" />
        </div>
        <button type="submit" disabled={loading || !templateId}
          className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
          Add
        </button>
      </div>
    </form>
  )
}

function NewSeqForm({ onClose, onSaved, onError }: {
  onClose: () => void
  onSaved: (id: number) => void
  onError: (msg: string) => void
}) {
  const [name, setName] = useState('')
  const [bcc, setBcc] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const seq = await createSequence({ name, bcc_email: bcc || undefined })
      onSaved(seq.id)
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-3 mb-3 space-y-2">
      <input required placeholder="Sequence name" value={name} onChange={e => setName(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500" />
      <input placeholder="BCC email (optional)" value={bcc} onChange={e => setBcc(e.target.value)}
        className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500" />
      <div className="flex gap-2">
        <button type="submit" disabled={loading}
          className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors">
          Create
        </button>
        <button type="button" onClick={onClose}
          className="py-1.5 px-3 border border-gray-300 dark:border-gray-600 text-xs rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors dark:text-gray-300">
          Cancel
        </button>
      </div>
    </form>
  )
}
