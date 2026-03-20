import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const { api_key } = await req.json()

  if (!api_key?.trim()) {
    return NextResponse.json({ error: 'API key is required' }, { status: 400 })
  }

  // Validate key against the backend (cheap request)
  try {
    const check = await fetch(`${API_URL}/analytics/summary`, {
      headers: { 'X-API-Key': api_key },
    })
    if (check.status === 401) {
      return NextResponse.json({ error: 'Invalid API key' }, { status: 401 })
    }
  } catch {
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 })
  }

  const res = NextResponse.json({ ok: true })
  res.cookies.set('ep_key', api_key, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30, // 30 days
  })
  return res
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true })
  res.cookies.delete('ep_key')
  return res
}
