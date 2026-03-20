import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/login', '/api/auth']

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Allow public paths and all /api/* routes (proxy handles 401)
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p)) || pathname.startsWith('/api/')) {
    return NextResponse.next()
  }

  const cookie = req.cookies.get('ep_key')
  if (!cookie?.value) {
    return NextResponse.redirect(new URL('/login', req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
