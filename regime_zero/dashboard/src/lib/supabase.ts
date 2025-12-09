import { createClient } from '@supabase/supabase-js'

console.log("Initializing Supabase Client...")

const envUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const envKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!envUrl) console.warn("Missing NEXT_PUBLIC_SUPABASE_URL, using placeholder")
if (!envKey) console.warn("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY, using placeholder")

const supabaseUrl = envUrl || "https://placeholder.supabase.co"
const supabaseKey = envKey || "placeholder_key"

export const supabase = createClient(supabaseUrl, supabaseKey)
