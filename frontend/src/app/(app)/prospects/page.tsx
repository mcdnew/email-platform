'use client'

import { useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  useReactTable, getCoreRowModel, flexRender,
  createColumnHelper, type RowSelectionState,
} from '@tanstack/react-table'
import {
  getProspects, createProspect, deleteProspect,
  bulkImportProspects, assignSequence, getSequences,
} from '@/lib/api'
import type { Prospect, ProspectCreate, Sequence } from '@/lib/types'
import { Toast } from '@/components/Toast'
import { PaginationBar } from '@/components/PaginationBar'
import { useToast } from '@/hooks/useToast'
import { Upload, Plus, ChevronUp, ChevronDown, Trash2, Link } from 'lucide-react'
import Papa from 'papaparse'

const SORT_FIELDS = ['name', 'email', 'company', 'created_at'] as const
// createColumnHelper has no dependencies — define once at module scope
const col = createColumnHelper<Prospect>()

export default function ProspectsPage() {
  const qc = useQueryClient()
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sortBy, setSortBy] = useState('name')
  const [order, setOrder] = useState('asc')
  const [showAddForm, setShowAddForm] = useState(false)
  const [assignModal, setAssignModal] = useState<number[] | null>(null)
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const { toast, showToast } = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['prospects', page, debouncedSearch, sortBy, order],
    queryFn: () => getProspects({ page, per_page: 50, sort_by: sortBy, order, search: debouncedSearch }),
  })

  const { data: sequences } = useQuery({ queryKey: ['sequences'], queryFn: getSequences })

  const deleteMut = useMutation({
    mutationFn: deleteProspect,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['prospects'] }); showToast('Deleted') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const assignMut = useMutation({
    mutationFn: assignSequence,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['prospects'] }); setAssignModal(null); showToast('Sequence assigned') },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  const bulkMut = useMutation({
    mutationFn: bulkImportProspects,
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['prospects'] })
      showToast(`Imported ${r.imported}, skipped ${r.skipped}`)
    },
    onError: (e: unknown) => showToast(e instanceof Error ? e.message : String(e), 'err'),
  })

  function handleSort(field: string) {
    if (sortBy === field) setOrder(o => o === 'asc' ? 'desc' : 'asc')
    else { setSortBy(field); setOrder('asc') }
    setPage(1)
  }

  function handleSearch(v: string) {
    setSearch(v)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => { setDebouncedSearch(v); setPage(1) }, 300)
  }

  function handleCSV(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    Papa.parse<Record<string, string>>(file, {
      header: true, skipEmptyLines: true,
      complete: (res) => {
        const items: ProspectCreate[] = res.data.map(row => ({
          name: row.name ?? row.Name ?? '',
          email: row.email ?? row.Email ?? '',
          company: row.company ?? row.Company,
          title: row.title ?? row.Title,
        })).filter(r => r.name && r.email)
        if (items.length === 0) { showToast('No valid rows found in CSV', 'err'); return }
        bulkMut.mutate(items)
      },
    })
    e.target.value = ''
  }

  const selectedIds = Object.entries(rowSelection).filter(([, v]) => v).map(([k]) => Number(k))

  // Stable column definition — only recreated if delete function changes
  const columns = useMemo(() => [
    col.display({
      id: 'select',
      header: ({ table }) => (
        <input type="checkbox"
          checked={table.getIsAllRowsSelected()}
          onChange={table.getToggleAllRowsSelectedHandler()}
          className="rounded"
        />
      ),
      cell: ({ row }) => (
        <input type="checkbox"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          className="rounded"
        />
      ),
    }),
    col.accessor('name', { header: 'Name' }),
    col.accessor('email', { header: 'Email' }),
    col.accessor('company', { header: 'Company', cell: i => i.getValue() ?? '—' }),
    col.accessor('title', { header: 'Title', cell: i => i.getValue() ?? '—' }),
    col.accessor('sequence_name', {
      header: 'Sequence',
      cell: i => {
        const v = i.getValue()
        const pct = i.row.original.sequence_progress_pct
        return v ? (
          <div>
            <div className="text-xs font-medium">{v}</div>
            <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
              <div className="bg-blue-500 h-1 rounded-full" style={{ width: `${pct}%` }} />
            </div>
          </div>
        ) : <span className="text-gray-400 text-xs">—</span>
      },
    }),
    col.display({
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <button onClick={() => deleteMut.mutate(row.original.id)}
          className="p-1 text-gray-400 hover:text-red-600 transition-colors">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      ),
    }),
  ], [deleteMut.mutate])

  const table = useReactTable({
    data: data?.items ?? [],
    columns,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    getRowId: row => String(row.id),
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    pageCount: data?.pages ?? 1,
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-gray-900">Prospects</h1>
        <div className="flex items-center gap-2">
          {selectedIds.length > 0 && (
            <button onClick={() => setAssignModal(selectedIds)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
              <Link className="w-3.5 h-3.5" />
              Assign sequence ({selectedIds.length})
            </button>
          )}
          <label className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 rounded-lg cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            Import CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleCSV} />
          </label>
          <button onClick={() => setShowAddForm(v => !v)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
            <Plus className="w-3.5 h-3.5" />
            Add prospect
          </button>
        </div>
      </div>

      {showAddForm && (
        <AddProspectForm
          onClose={() => setShowAddForm(false)}
          onSaved={() => { setShowAddForm(false); qc.invalidateQueries({ queryKey: ['prospects'] }); showToast('Prospect added') }}
          onError={(msg) => showToast(msg, 'err')}
        />
      )}

      <div className="mb-3">
        <input
          type="search"
          placeholder="Search name, email, company…"
          value={search}
          onChange={e => handleSearch(e.target.value)}
          className="w-80 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(header => {
                  const sortable = (SORT_FIELDS as readonly string[]).includes(header.id)
                  return (
                    <th key={header.id}
                      onClick={sortable ? () => handleSort(header.id) : undefined}
                      className={`px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide ${sortable ? 'cursor-pointer hover:text-gray-900 select-none' : ''}`}>
                      <div className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sortable && sortBy === header.id && (
                          order === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                        )}
                      </div>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="px-3 py-8 text-center text-gray-400 text-sm">Loading…</td></tr>
            ) : table.getRowModel().rows.length === 0 ? (
              <tr><td colSpan={7} className="px-3 py-12 text-center">
                <p className="text-gray-500 text-sm font-medium">No prospects yet</p>
                <p className="text-gray-400 text-xs mt-1">Import a CSV or add your first prospect above.</p>
              </td></tr>
            ) : table.getRowModel().rows.map(row => (
              <tr key={row.id} className="hover:bg-gray-50">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-3 py-2.5 text-gray-700">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {data && data.pages > 1 && (
          <PaginationBar
            total={data.total}
            page={data.page}
            pages={data.pages}
            label="prospects"
            onPageChange={setPage}
          />
        )}
      </div>

      {assignModal && sequences && (
        <AssignModal
          prospectIds={assignModal}
          sequences={sequences}
          onClose={() => setAssignModal(null)}
          onAssign={(seqId) => assignMut.mutate({ prospect_ids: assignModal, sequence_id: seqId })}
        />
      )}

      <Toast toast={toast} />
    </div>
  )
}

function AddProspectForm({ onClose, onSaved, onError }: {
  onClose: () => void
  onSaved: () => void
  onError: (msg: string) => void
}) {
  const [form, setForm] = useState({ name: '', email: '', company: '', title: '' })
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await createProspect({ name: form.name, email: form.email, company: form.company || undefined, title: form.title || undefined })
      onSaved()
    } catch (e: unknown) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={submit} className="bg-white rounded-xl border border-gray-200 p-4 mb-4 grid grid-cols-4 gap-3 items-end">
      {(['name', 'email', 'company', 'title'] as const).map(f => (
        <div key={f}>
          <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">{f}</label>
          <input required={f === 'name' || f === 'email'} value={form[f]}
            onChange={e => setForm(v => ({ ...v, [f]: e.target.value }))}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      ))}
      <div className="flex gap-2">
        <button type="submit" disabled={loading}
          className="flex-1 py-1.5 px-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
          Save
        </button>
        <button type="button" onClick={onClose}
          className="py-1.5 px-3 bg-white hover:bg-gray-50 border border-gray-300 text-sm rounded-lg transition-colors">
          Cancel
        </button>
      </div>
    </form>
  )
}

function AssignModal({ prospectIds, sequences, onClose, onAssign }: {
  prospectIds: number[]
  sequences: Sequence[]
  onClose: () => void
  onAssign: (seqId: number) => void
}) {
  const [seqId, setSeqId] = useState<number | ''>('')
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-80">
        <h3 className="text-sm font-semibold mb-3">Assign sequence to {prospectIds.length} prospect{prospectIds.length > 1 ? 's' : ''}</h3>
        <select value={seqId} onChange={e => setSeqId(Number(e.target.value))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="">Select a sequence…</option>
          {sequences.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <div className="flex gap-2">
          <button disabled={!seqId} onClick={() => onAssign(Number(seqId))}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            Assign
          </button>
          <button onClick={onClose}
            className="py-2 px-4 bg-white hover:bg-gray-50 border border-gray-300 text-sm rounded-lg transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
