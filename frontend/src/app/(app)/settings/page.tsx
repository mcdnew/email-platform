'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { runScheduler, forceScheduler, sendTestEmail, getErrorLog, clearErrorLog, getSmtpSettings, updateSmtpSettings } from '@/lib/api'
import type { LogEntry } from '@/lib/api'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Play, Zap, Send, RefreshCw, Trash2, Save } from 'lucide-react'

export default function SettingsPage() {
  const { toast, showToast } = useToast()
  const [testForm, setTestForm] = useState({ email: '', subject: 'Test email', body: 'Hi {{name}}, this is a test.' })
  const [loading, setLoading] = useState<string | null>(null)

  async function run(label: string, fn: () => Promise<{ message?: string }>) {
    setLoading(label)
    try {
      const r = await fn()
      showToast(r.message ?? 'Done')
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : String(e), 'err')
    } finally {
      setLoading(null)
    }
  }

  async function handleTestEmail(e: React.FormEvent) {
    e.preventDefault()
    run('test', () => sendTestEmail(testForm))
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Settings</h1>

      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mb-4">
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">Scheduler</h2>
        <p className="text-xs text-gray-500 mb-4">Manually trigger the email send loop.</p>
        <div className="flex gap-3">
          <button
            onClick={() => run('run', runScheduler)}
            disabled={loading !== null}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            {loading === 'run' ? 'Running…' : 'Run scheduler'}
          </button>
          <button
            onClick={() => run('force', forceScheduler)}
            disabled={loading !== null}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Zap className="w-3.5 h-3.5" />
            {loading === 'force' ? 'Running…' : 'Force send (ignore limits)'}
          </button>
        </div>
      </section>

      <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">Send test email</h2>
        <p className="text-xs text-gray-500 mb-4">Send a test to verify SMTP configuration.</p>
        <form onSubmit={handleTestEmail} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">To</label>
            <input required type="email" value={testForm.email}
              onChange={e => setTestForm(v => ({ ...v, email: e.target.value }))}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500"
              suppressHydrationWarning />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Subject</label>
            <input required value={testForm.subject}
              onChange={e => setTestForm(v => ({ ...v, subject: e.target.value }))}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500"
              suppressHydrationWarning />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Body</label>
            <textarea rows={4} value={testForm.body}
              onChange={e => setTestForm(v => ({ ...v, body: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500" />
          </div>
          <button type="submit" disabled={loading !== null}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            <Send className="w-3.5 h-3.5" />
            {loading === 'test' ? 'Sending…' : 'Send test'}
          </button>
        </form>
      </section>

      <SmtpSettingsForm />

      <LogViewer />

      <Toast toast={toast} />
    </div>
  )
}

// ── SMTP Settings Form ───────────────────────────────────────────────────────
function SmtpSettingsForm() {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const { data, isLoading } = useQuery({ queryKey: ['smtp-settings'], queryFn: getSmtpSettings })

  const [form, setForm] = useState({ smtp_server: '', smtp_port: '', smtp_user: '', smtp_password: '', smtp_bcc: '' })
  const [dirty, setDirty] = useState(false)

  // Populate form once data loads (only if user hasn't started editing)
  if (data && !dirty && form.smtp_server === '') {
    setForm({
      smtp_server: data.smtp_server ?? '',
      smtp_port: String(data.smtp_port ?? ''),
      smtp_user: data.smtp_user ?? '',
      smtp_password: '',
      smtp_bcc: data.smtp_bcc ?? '',
    })
  }

  const saveMut = useMutation({
    mutationFn: () => updateSmtpSettings({
      smtp_server: form.smtp_server || undefined,
      smtp_port: form.smtp_port ? Number(form.smtp_port) : undefined,
      smtp_user: form.smtp_user || undefined,
      smtp_password: form.smtp_password || undefined,
      smtp_bcc: form.smtp_bcc,
    }),
    onSuccess: (r) => {
      showToast(r.message ?? 'Saved')
      setDirty(false)
      qc.invalidateQueries({ queryKey: ['smtp-settings'] })
    },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  function field(label: string, key: keyof typeof form, type = 'text', placeholder = '') {
    return (
      <div key={key}>
        <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</label>
        <input
          type={type}
          value={form[key]}
          placeholder={placeholder}
          onChange={e => { setForm(v => ({ ...v, [key]: e.target.value })); setDirty(true) }}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500"
          suppressHydrationWarning
        />
      </div>
    )
  }

  return (
    <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mb-4">
      <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1">SMTP Configuration</h2>
      <p className="text-xs text-gray-500 mb-4">
        Override the server-level SMTP env vars.
        {data?.source === 'env' && <span className="ml-1 text-amber-600 dark:text-amber-400">(currently using .env defaults)</span>}
        {data?.source === 'db' && <span className="ml-1 text-green-600 dark:text-green-400">(overrides active)</span>}
      </p>
      {isLoading ? (
        <p className="text-xs text-gray-400">Loading…</p>
      ) : (
        <form onSubmit={e => { e.preventDefault(); saveMut.mutate() }} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">{field('SMTP Server', 'smtp_server', 'text', 'smtp.gmail.com')}</div>
            <div>{field('Port', 'smtp_port', 'number', '587')}</div>
          </div>
          {field('Username / From address', 'smtp_user', 'email', 'you@example.com')}
          {field('Password', 'smtp_password', 'password', '(leave blank to keep current)')}
          {field('BCC (optional)', 'smtp_bcc', 'email', 'manager@example.com')}
          <button type="submit" disabled={saveMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            <Save className="w-3.5 h-3.5" />
            {saveMut.isPending ? 'Saving…' : 'Save SMTP settings'}
          </button>
        </form>
      )}
    </section>
  )
}

// ── Known fields stripped from context display ────────────────────────────
const KNOWN_FIELDS = new Set(['timestamp', 'level', 'logger', 'event'])

const LEVEL_STYLES: Record<string, string> = {
  DEBUG:    'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
  INFO:     'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
  WARNING:  'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
  ERROR:    'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
  CRITICAL: 'bg-red-200 dark:bg-red-900/50 text-red-800 dark:text-red-300',
}

function fmtTime(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return ts }
}

function LogViewer() {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const [enabled, setEnabled] = useState(false)

  const { data, isFetching, error } = useQuery({
    queryKey: ['error-log'],
    queryFn: getErrorLog,
    enabled,
    refetchOnWindowFocus: false,
    retry: false,
  })

  const clearMut = useMutation({
    mutationFn: clearErrorLog,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['error-log'] }); showToast('Log cleared') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const entries = data?.entries ?? []

  return (
    <section className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 mt-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Activity log</h2>
          <p className="text-xs text-gray-500 mt-0.5">Structured JSON log from the backend (DEV_MODE only).</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setEnabled(true); qc.invalidateQueries({ queryKey: ['error-log'] }) }}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isFetching ? 'animate-spin' : ''}`} />
            {isFetching ? 'Loading…' : 'Load / Refresh'}
          </button>
          {entries.length > 0 && (
            <button
              onClick={() => clearMut.mutate()}
              disabled={clearMut.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 rounded-lg transition-colors"
            >
              <Trash2 className="w-3 h-3" /> Clear
            </button>
          )}
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-500 py-4 text-center">
          {error instanceof Error ? error.message : 'Failed to load log'}
        </p>
      )}

      {!enabled && !error && (
        <p className="text-xs text-gray-400 py-6 text-center">Click "Load / Refresh" to view the log.</p>
      )}

      {enabled && !isFetching && !error && entries.length === 0 && (
        <p className="text-xs text-gray-400 py-6 text-center">Log is empty.</p>
      )}

      {entries.length > 0 && (
        <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-100 dark:border-gray-800 divide-y divide-gray-50 dark:divide-gray-800/50">
          {[...entries].reverse().map((entry, i) => (
            <LogRow key={i} entry={entry} />
          ))}
        </div>
      )}
    </section>
  )
}

function LogRow({ entry }: { entry: LogEntry }) {
  const level = entry.level ?? 'INFO'
  const ctx = Object.entries(entry).filter(([k]) => !KNOWN_FIELDS.has(k))

  return (
    <div className="flex items-start gap-2.5 px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 text-xs font-mono">
      <span className="text-gray-400 shrink-0 w-20">{fmtTime(entry.timestamp)}</span>
      <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${LEVEL_STYLES[level] ?? LEVEL_STYLES.INFO}`}>
        {level}
      </span>
      <span className="font-semibold text-gray-800 dark:text-gray-200 shrink-0">{entry.event}</span>
      {ctx.length > 0 && (
        <span className="text-gray-500 break-all">
          {ctx.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join('  ')}
        </span>
      )}
    </div>
  )
}
