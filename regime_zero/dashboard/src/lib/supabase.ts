import { createClient } from '@supabase/supabase-js'

const supabaseUrl = "https://ywkqvhtwjxclvjcdcyrv.supabase.co"
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl3a3F2aHR3anhjbHZqY2RjeXJ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk2OTU5OCwiZXhwIjoyMDc5NTQ1NTk4fQ.40TrXj4Oyjz5qDkRA0kdoKtXZD1gKkWxmU9faedudfQ"

export const supabase = createClient(supabaseUrl, supabaseKey)
