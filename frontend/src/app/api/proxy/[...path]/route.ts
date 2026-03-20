import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

async function proxy(req: NextRequest, params: { path: string[] }) {
  const cookieStore = cookies()
  const apiKey = cookieStore.get('ep_key')?.value

  const path = params.path.join('/')
  const search = req.nextUrl.search
  const url = `${API_URL}/${path}${search}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (apiKey) headers['X-API-Key'] = apiKey

  let body: BodyInit | undefined
  if (!['GET', 'DELETE', 'HEAD'].includes(req.method)) {
    body = await req.text()
  }

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body,
  })

  const data = await upstream.text()
  return new NextResponse(data, {
    status: upstream.status,
    headers: { 'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json' },
  })
}

export const GET = (req: NextRequest, ctx: { params: { path: string[] } }) => proxy(req, ctx.params)
export const POST = (req: NextRequest, ctx: { params: { path: string[] } }) => proxy(req, ctx.params)
export const PUT = (req: NextRequest, ctx: { params: { path: string[] } }) => proxy(req, ctx.params)
export const PATCH = (req: NextRequest, ctx: { params: { path: string[] } }) => proxy(req, ctx.params)
export const DELETE = (req: NextRequest, ctx: { params: { path: string[] } }) => proxy(req, ctx.params)
