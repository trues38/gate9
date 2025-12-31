import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

// Routes that require authentication
const AUTH_REQUIRED_ROUTES = ['/dashboard', '/matches', '/report', '/regime-ai']

// Routes that require active subscription
const SUBSCRIPTION_REQUIRED_ROUTES = ['/matches']

// Routes that should redirect logged-in users
const AUTH_ROUTES = ['/login', '/signup']

// Subdomain configuration
const SUBDOMAIN_MAP: Record<string, string> = {
  'kr': 'KR',
  'us': 'US',
  'jp': 'JP',
  'cn': 'CN',
  'eu': 'EU',
  'crypto': 'CRYPTO'
}

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  const hostname = request.headers.get('host') || ''

  // Skip middleware for static files and API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.') // files with extensions
  ) {
    return NextResponse.next()
  }

  // Update Supabase session
  const { response, user, supabase } = await updateSession(request)

  // Handle subdomain routing
  const currentHost = process.env.NODE_ENV === 'production'
    ? hostname.replace('.regimezero.com', '')
    : hostname.replace('.localhost:3000', '')

  const countryCode = SUBDOMAIN_MAP[currentHost]

  if (countryCode) {
    const url = request.nextUrl.clone()

    if (url.pathname === '/') {
      url.pathname = '/dashboard'
    }

    if (url.pathname.startsWith('/dashboard')) {
      url.searchParams.set('country', countryCode)
      return NextResponse.rewrite(url)
    }
  }

  // Check if route requires authentication
  const requiresAuth = AUTH_REQUIRED_ROUTES.some(route =>
    pathname.startsWith(route)
  )

  // Check if route requires subscription
  const requiresSubscription = SUBSCRIPTION_REQUIRED_ROUTES.some(route =>
    pathname.startsWith(route)
  )

  // Redirect to login if auth required but not logged in
  if (requiresAuth && !user) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Check subscription for protected routes
  if (requiresSubscription && user) {
    const { data: subscription } = await supabase
      .from('subscriptions')
      .select('expires_at, status')
      .eq('user_id', user.id)
      .eq('status', 'active')
      .gte('expires_at', new Date().toISOString())
      .order('expires_at', { ascending: false })
      .limit(1)
      .single()

    if (!subscription) {
      const pricingUrl = new URL('/pricing', request.url)
      pricingUrl.searchParams.set('reason', 'subscription_required')
      return NextResponse.redirect(pricingUrl)
    }
  }

  // Redirect logged-in users away from auth pages
  if (AUTH_ROUTES.includes(pathname) && user) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|sw.js|offline.html).*)',
  ],
}
