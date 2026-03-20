import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/login', '/api/auth']

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  if (PUBLIC_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const apiKey = req.cookies.get('ep_key')?.value

  // For proxy requests: no key → return 401 immediately (don't hit backend)
  if (pathname.startsWith('/api/proxy')) {
    if (!apiKey) return new NextResponse('Unauthorized', { status: 401 })
    return NextResponse.next()
  }

  // For page routes: no key → redirect to login
  if (!apiKey) {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
