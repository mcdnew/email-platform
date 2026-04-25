'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getActivityEvents, getConversations, getLeadCaptures, getProspects, reviewLeadCapture } from '@/lib/api'

function parseJson(value: string | null): Record<string, unknown> {
  if (!value) return {}
  try {
    return JSON.parse(value) as Record<string, unknown>
  } catch {
    return {}
  }
}

export default function AcquirePage() {
  const qc = useQueryClient()
  const { data: pendingCaptures, isLoading: capturesLoading } = useQuery({
    queryKey: ['lead-captures', 'pending_review'],
    queryFn: () => getLeadCaptures({ review_status: 'pending_review', source_type: 'web_discovery' }),
  })
  const { data: interestedProspects, isLoading: interestedLoading } = useQuery({
    queryKey: ['prospects', 'interested'],
    queryFn: () => getProspects({ lifecycle_stage: 'interested', per_page: 25, page: 1 }),
  })
  const { data: recentAcquireEvents, isLoading: eventsLoading } = useQuery({
    queryKey: ['activity-events', 'acquire'],
    queryFn: () => getActivityEvents({ source_module: 'acquire', limit: 8 }),
  })
  const { data: gmailConversations, isLoading: conversationsLoading } = useQuery({
    queryKey: ['conversations', 'gmail'],
    queryFn: () => getConversations({ channel: 'gmail', limit: 8 }),
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, review_status }: { id: number; review_status: 'approved' | 'rejected' }) =>
      reviewLeadCapture(id, { review_status }),
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['lead-captures'] }),
        qc.invalidateQueries({ queryKey: ['prospects'] }),
      ])
    },
  })

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Acquire</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Pending discovered leads and high-signal outreach contacts now owned by the core platform.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Pending Discovery Review</h2>
            <span className="text-xs text-gray-400">{pendingCaptures?.length ?? 0} items</span>
          </div>
          {capturesLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !pendingCaptures?.length ? (
            <p className="text-sm text-gray-500">No pending discovered leads.</p>
          ) : (
            <div className="space-y-3">
              {pendingCaptures.map((capture) => {
                const normalized = parseJson(capture.normalized_payload_json)
                const company = normalized.company as string | undefined
                const email = normalized.email as string | undefined
                const fact = normalized.fact as string | undefined
                const name = normalized.name as string | undefined
                return (
                  <div key={capture.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {name || company || capture.external_ref || `Lead #${capture.id}`}
                        </div>
                        <div className="text-xs text-gray-500 mt-1 truncate">
                          {[company, email].filter(Boolean).join(' • ') || 'No canonical email yet'}
                        </div>
                        {fact && <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">{fact}</p>}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => reviewMutation.mutate({ id: capture.id, review_status: 'approved' })}
                          className="px-2.5 py-1.5 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
                          disabled={reviewMutation.isPending}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => reviewMutation.mutate({ id: capture.id, review_status: 'rejected' })}
                          className="px-2.5 py-1.5 text-xs rounded-md bg-gray-200 text-gray-800 hover:bg-gray-300 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
                          disabled={reviewMutation.isPending}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Interested Contacts</h2>
            <span className="text-xs text-gray-400">{interestedProspects?.total ?? 0} contacts</span>
          </div>
          {interestedLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !interestedProspects?.items.length ? (
            <p className="text-sm text-gray-500">No contacts are currently marked interested.</p>
          ) : (
            <div className="space-y-3">
              {interestedProspects.items.map((prospect) => (
                <div key={prospect.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{prospect.name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[prospect.company, prospect.email].filter(Boolean).join(' • ')}
                  </div>
                  <div className="mt-2 text-[11px] uppercase tracking-wide text-amber-600 dark:text-amber-400">
                    {prospect.lifecycle_stage || 'interested'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Recent Acquisition Activity</h2>
            <span className="text-xs text-gray-400">{recentAcquireEvents?.length ?? 0} events</span>
          </div>
          {eventsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !recentAcquireEvents?.length ? (
            <p className="text-sm text-gray-500">No recent acquisition activity.</p>
          ) : (
            <div className="space-y-3">
              {recentAcquireEvents.map((event) => (
                <div key={event.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{event.event_type}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[event.campaign_key, event.created_at].filter(Boolean).join(' • ')}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Gmail Conversations</h2>
            <span className="text-xs text-gray-400">{gmailConversations?.length ?? 0} threads</span>
          </div>
          {conversationsLoading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : !gmailConversations?.length ? (
            <p className="text-sm text-gray-500">No mirrored Gmail conversations yet.</p>
          ) : (
            <div className="space-y-3">
              {gmailConversations.map((conversation) => (
                <div key={conversation.id} className="rounded-lg border border-gray-100 dark:border-gray-800 p-3">
                  <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {conversation.provider_thread_id || `Conversation #${conversation.id}`}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {[conversation.campaign_key, conversation.state].filter(Boolean).join(' • ')}
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
