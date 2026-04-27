'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteProspect, getActivityEventsByProspect, getConversationsByProspect, getProspect, getProspectTimeline, updateProspect, updateProspectLifecycle } from '@/lib/api'

export default function AcquireProspectDetailPage() {
  const params = useParams<{ prospectId: string }>()
  const prospectId = Number(params.prospectId)
  const router = useRouter()
  const qc = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', company: '', title: '', phone: '', notes: '' })

  const { data: prospect, isLoading: prospectLoading } = useQuery({
    queryKey: ['acquire-prospect', prospectId],
    queryFn: () => getProspect(prospectId),
    enabled: Number.isFinite(prospectId),
  })
  const { data: activityEvents, isLoading: eventsLoading } = useQuery({
    queryKey: ['activity-events', 'prospect', prospectId],
    queryFn: () => getActivityEventsByProspect(prospectId, { limit: 20 }),
    enabled: Number.isFinite(prospectId),
  })
  const { data: conversations, isLoading: conversationsLoading } = useQuery({
    queryKey: ['conversations', 'prospect', prospectId],
    queryFn: () => getConversationsByProspect(prospectId, { limit: 20 }),
    enabled: Number.isFinite(prospectId),
  })
  const { data: timeline, isLoading: timelineLoading } = useQuery({
    queryKey: ['prospect-timeline', prospectId],
    queryFn: () => getProspectTimeline(prospectId),
    enabled: Number.isFinite(prospectId),
  })
  const lifecycleMutation = useMutation({
    mutationFn: ({ targetStage, notes }: { targetStage: string; notes?: string }) =>
      updateProspectLifecycle(prospectId, { target_stage: targetStage, notes }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['prospects'] }),
        qc.invalidateQueries({ queryKey: ['activity-events'] }),
        qc.invalidateQueries({ queryKey: ['conversations'] }),
      ])
    },
  })
  const saveMutation = useMutation({
    mutationFn: () => updateProspect(prospectId, {
      name: form.name,
      email: form.email,
      company: form.company || undefined,
      title: form.title || undefined,
      phone: form.phone || undefined,
      notes: form.notes || undefined,
    }),
    onSuccess: async () => {
      setIsEditing(false)
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['acquire-prospect', prospectId] }),
        qc.invalidateQueries({ queryKey: ['prospects'] }),
      ])
    },
  })
  const deleteMutation = useMutation({
    mutationFn: () => deleteProspect(prospectId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['prospects'] })
      router.push('/acquire')
    },
  })

  useEffect(() => {
    if (!prospect) return
    setForm({
      name: prospect.name ?? '',
      email: prospect.email ?? '',
      company: prospect.company ?? '',
      title: prospect.title ?? '',
      phone: prospect.phone ?? '',
      notes: prospect.notes ?? '',
    })
  }, [prospect])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href="/acquire" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
            ← Back to Acquire
          </Link>
          <h1 className="mt-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
            {prospect?.name || `Prospect #${prospectId}`}
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {[prospect?.company, prospect?.email, prospect?.lifecycle_stage].filter(Boolean).join(' • ')}
          </p>
        </div>
        {prospect && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setIsEditing((value) => !value)}
              className="px-3 py-2 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-700"
            >
              {isEditing ? 'Cancel edit' : 'Edit prospect'}
            </button>
            <button
              onClick={() => {
                if (!window.confirm(`Delete ${prospect.name}? This cannot be undone.`)) return
                deleteMutation.mutate()
              }}
              className="px-3 py-2 text-xs rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              disabled={deleteMutation.isPending}
            >
              Delete prospect
            </button>
            {prospect.lifecycle_stage === 'interested' && (
              <button
                onClick={() => lifecycleMutation.mutate({ targetStage: 'qualified', notes: 'Qualified from acquisition detail view' })}
                className="px-3 py-2 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                disabled={lifecycleMutation.isPending}
              >
                Mark qualified
              </button>
            )}
            {prospect.lifecycle_stage !== 'lost' && prospect.lifecycle_stage !== 'archived' && (
              <button
                onClick={() => lifecycleMutation.mutate({ targetStage: 'lost' })}
                className="px-3 py-2 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
                disabled={lifecycleMutation.isPending}
              >
                Mark lost
              </button>
            )}
            {prospect.lifecycle_stage === 'lost' && (
              <button
                onClick={() => lifecycleMutation.mutate({ targetStage: 'archived' })}
                className="px-3 py-2 text-xs rounded-md bg-gray-900 text-white hover:bg-black dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50"
                disabled={lifecycleMutation.isPending}
              >
                Archive
              </button>
            )}
          </div>
        )}
      </div>

      {prospect && isEditing && (
        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {([
              ['name', 'Name'],
              ['email', 'Email'],
              ['company', 'Company'],
              ['title', 'Title'],
              ['phone', 'Phone'],
            ] as const).map(([field, label]) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
                <input
                  value={form[field]}
                  onChange={(event) => setForm((current) => ({ ...current, [field]: event.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
                />
              </div>
            ))}
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Notes</label>
              <textarea
                value={form.notes}
                onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                rows={4}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Save changes
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="px-4 py-2 text-sm rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <section className="xl:col-span-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Mirrored Conversations</h2>
          {conversationsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !conversations?.length ? (
            <p className="text-sm text-gray-500">No conversation records yet.</p>
          ) : (
            <div className="space-y-3">
              {conversations.map((conversation) => (
                <div key={conversation.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {conversation.provider_thread_id || `Conversation #${conversation.id}`}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[conversation.channel, conversation.state, conversation.campaign_key].filter(Boolean).join(' • ')}
                  </div>
                  {conversation.last_message_at && (
                    <div className="mt-2 text-[11px] text-gray-400">Last message: {conversation.last_message_at}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="xl:col-span-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Recent Activity</h2>
          {eventsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !activityEvents?.length ? (
            <p className="text-sm text-gray-500">No recorded activity yet.</p>
          ) : (
            <div className="space-y-3">
              {activityEvents.map((event) => (
                <div key={event.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{event.event_type}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[event.source_module, event.campaign_key, event.created_at].filter(Boolean).join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="xl:col-span-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Nurture Timeline</h2>
          {timelineLoading || prospectLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !timeline?.length ? (
            <p className="text-sm text-gray-500">No scheduled nurture timeline yet.</p>
          ) : (
            <div className="space-y-3">
              {timeline.map((entry, index) => (
                <div key={`${entry.template_name}-${index}`} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Step {entry.step_number ?? index + 1} · {entry.template_name}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[entry.status, entry.scheduled_at, entry.sent_at].filter(Boolean).join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
