import { createBrowserClient } from '@supabase/ssr'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export function createClient() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    // Return a mock client for build time
    console.warn('Supabase credentials not configured')
  }
  return createBrowserClient(
    SUPABASE_URL || 'https://placeholder.supabase.co',
    SUPABASE_ANON_KEY || 'placeholder_key'
  )
}

// Singleton instance for client components
let client: ReturnType<typeof createBrowserClient> | null = null

export function getClient() {
  if (!client) {
    client = createClient()
  }
  return client
}
