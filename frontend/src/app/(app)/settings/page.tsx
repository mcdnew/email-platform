'use client'

import { useState } from 'react'
import { runScheduler, forceScheduler, sendTestEmail } from '@/lib/api'
import { Toast } from '@/components/Toast'
import { useToast } from '@/hooks/useToast'
import { Play, Zap, Send } from 'lucide-react'

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
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Settings</h1>

      <section className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Scheduler</h2>
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

      <section className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Send test email</h2>
        <p className="text-xs text-gray-500 mb-4">Send a test to verify SMTP configuration.</p>
        <form onSubmit={handleTestEmail} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">To</label>
            <input required type="email" value={testForm.email}
              onChange={e => setTestForm(v => ({ ...v, email: e.target.value }))}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Subject</label>
            <input required value={testForm.subject}
              onChange={e => setTestForm(v => ({ ...v, subject: e.target.value }))}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Body</label>
            <textarea rows={4} value={testForm.body}
              onChange={e => setTestForm(v => ({ ...v, body: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          </div>
          <button type="submit" disabled={loading !== null}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            <Send className="w-3.5 h-3.5" />
            {loading === 'test' ? 'Sending…' : 'Send test'}
          </button>
        </form>
      </section>

      <Toast toast={toast} />
    </div>
  )
}
