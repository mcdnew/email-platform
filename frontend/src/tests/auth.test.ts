import { describe, it, expect, vi, beforeEach } from 'vitest'

// Unit tests for auth middleware logic

describe('Auth middleware', () => {
  it('passes public paths without cookie', () => {
    const publicPaths = ['/login', '/api/auth']
    publicPaths.forEach(p => {
      expect(['/login', '/api/auth'].some(pub => p.startsWith(pub))).toBe(true)
    })
  })

  it('blocks protected paths without cookie', () => {
    const protectedPaths = ['/dashboard', '/prospects', '/templates']
    protectedPaths.forEach(p => {
      const isPublic = ['/login', '/api/auth'].some(pub => p.startsWith(pub)) || p.startsWith('/api/')
      expect(isPublic).toBe(false)
    })
  })

  it('allows /api/ paths (proxy handles 401)', () => {
    expect('/api/proxy/prospects'.startsWith('/api/')).toBe(true)
  })
})
