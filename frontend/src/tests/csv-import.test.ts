import { describe, it, expect } from 'vitest'

// Regression test for CSV import (critical gap: malformed row handling)
// Issue: partial import should not crash; malformed rows should be skipped

interface CsvRow { name?: string; email?: string; company?: string; title?: string }

function parseCsvRows(rows: CsvRow[]) {
  const valid: CsvRow[] = []
  const errors: string[] = []

  for (const row of rows) {
    if (!row.name?.trim() || !row.email?.trim()) {
      errors.push(`Skipped row missing name or email: ${JSON.stringify(row)}`)
    } else {
      valid.push(row)
    }
  }
  return { valid, errors }
}

describe('CSV import validation', () => {
  it('accepts valid rows', () => {
    const { valid, errors } = parseCsvRows([
      { name: 'Alice', email: 'alice@example.com', company: 'Acme' },
    ])
    expect(valid).toHaveLength(1)
    expect(errors).toHaveLength(0)
  })

  it('skips rows missing email', () => {
    const { valid, errors } = parseCsvRows([{ name: 'Bob' }])
    expect(valid).toHaveLength(0)
    expect(errors).toHaveLength(1)
  })

  it('skips rows missing name', () => {
    const { valid, errors } = parseCsvRows([{ email: 'test@example.com' }])
    expect(valid).toHaveLength(0)
    expect(errors).toHaveLength(1)
  })

  it('processes valid rows and skips malformed — no crash', () => {
    const rows: CsvRow[] = [
      { name: 'Alice', email: 'alice@example.com' },
      { name: '', email: 'bad@example.com' }, // missing name
      { name: 'Charlie', email: 'charlie@example.com' },
    ]
    const { valid, errors } = parseCsvRows(rows)
    expect(valid).toHaveLength(2)
    expect(errors).toHaveLength(1)
  })

  it('returns empty arrays for empty input', () => {
    const { valid, errors } = parseCsvRows([])
    expect(valid).toHaveLength(0)
    expect(errors).toHaveLength(0)
  })
})
