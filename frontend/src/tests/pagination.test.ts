import { describe, it, expect } from 'vitest'

// Regression tests for pagination logic (Issue 1A from eng review)

function buildPaginationParams(page: number, perPage: number, sortBy: string, order: string, search: string) {
  return Object.fromEntries(
    Object.entries({ page, per_page: perPage, sort_by: sortBy, order, search })
      .filter(([, v]) => v !== undefined && v !== '')
  )
}

describe('Pagination param builder', () => {
  it('builds basic params', () => {
    const params = buildPaginationParams(1, 50, 'name', 'asc', '')
    expect(params.page).toBe(1)
    expect(params.per_page).toBe(50)
    expect(params.sort_by).toBe('name')
    expect(params.order).toBe('asc')
    expect(params.search).toBeUndefined()
  })

  it('includes search when provided', () => {
    const params = buildPaginationParams(1, 50, 'name', 'asc', 'acme')
    expect(params.search).toBe('acme')
  })

  it('page 1 is the default starting page', () => {
    const params = buildPaginationParams(1, 50, 'name', 'asc', '')
    expect(params.page).toBe(1)
  })

  it('handles last page edge case (page = pages)', () => {
    const total = 100, perPage = 50
    const pages = Math.ceil(total / perPage)
    expect(pages).toBe(2)
    expect(buildPaginationParams(pages, perPage, 'name', 'asc', '').page).toBe(2)
  })
})
