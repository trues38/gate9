import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
    const hostname = request.headers.get('host') || ''

    // Define allowed subdomains/countries
    const subdomainMap: Record<string, string> = {
        'kr': 'KR',
        'us': 'US',
        'jp': 'JP',
        'cn': 'CN',
        'eu': 'EU',
        'crypto': 'CRYPTO'
    }

    // Check if we are on a subdomain
    // Example: kr.regimezero.com -> subdomain is 'kr'
    // Localhost handling: kr.localhost:3000 (requires /etc/hosts edit to test locally)
    const currentHost = process.env.NODE_ENV === 'production'
        ? hostname.replace('.regimezero.com', '')
        : hostname.replace('.localhost:3000', '')

    const countryCode = subdomainMap[currentHost]

    if (countryCode) {
        // Clone the URL
        const url = request.nextUrl.clone()

        // If accessing root, redirect to dashboard
        if (url.pathname === '/') {
            url.pathname = '/dashboard'
        }

        // Add country param if it's the dashboard path
        if (url.pathname.startsWith('/dashboard')) {
            url.searchParams.set('country', countryCode)
            return NextResponse.rewrite(url)
        }
    }

    return NextResponse.next()
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
}
