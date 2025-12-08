
import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import path from 'path'

// Load env from dashboard/.env.local or root .env
// For simplicity, we'll try to use the hardcoded values from src/lib/supabase.ts if possible, 
// but since this is a standalone script, we might need to rely on process.env or just ask user to set it.
// Actually, let's try to read from the file or just use placeholders if we can't find them.

// We will assume the user has set up the env vars or we can import from the dashboard config if we use ts-node properly.
// But to be safe and quick, I'll use the values I saw in src/lib/supabase.ts earlier if I can recall them, 
// OR I will try to load from .env.

// Wait, I saw src/lib/supabase.ts had hardcoded values in a previous turn (Step 193 summary says "Supabase credentials were temporarily hardcoded").
// I will check src/lib/supabase.ts content to see if I can use them here for the seed script.

// For now, I'll write a script that expects env vars.

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_KEY

if (!supabaseUrl || !supabaseKey) {
    console.error('Missing Supabase URL or Key')
    process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseKey)

const sampleNews = [
    {
        title: "Fed's Waller Signals Rate Cut in Q1",
        summary: "Federal Reserve Governor Christopher Waller indicated that recent inflation data supports a pivot to rate cuts early next year.",
        url: "https://www.bloomberg.com/news/articles/2025-12-03/fed-waller-signals-rate-cut",
        source: "Bloomberg",
        country: "US",
        published_at: new Date().toISOString()
    },
    {
        title: "ECB Holds Rates Steady Amid Growth Concerns",
        summary: "The European Central Bank maintained its key interest rates, citing persistent but cooling inflation and weak economic growth.",
        url: "https://www.reuters.com/markets/europe/ecb-holds-rates",
        source: "Reuters",
        country: "EU",
        published_at: new Date(Date.now() - 1000 * 60 * 5).toISOString() // 5 mins ago
    },
    {
        title: "Bitcoin Surges Past $98k on ETF Inflows",
        summary: "Crypto markets rallied as institutional inflows into spot Bitcoin ETFs hit a record high for the third consecutive day.",
        url: "https://www.coindesk.com/markets/2025/12/03/bitcoin-surges",
        source: "CoinDesk",
        country: "CRYPTO",
        published_at: new Date(Date.now() - 1000 * 60 * 12).toISOString() // 12 mins ago
    },
    {
        title: "Bank of Korea Hints at Policy Pivot",
        summary: "BOK Governor Rhee stated that domestic demand conditions may warrant a shift in monetary policy stance sooner than expected.",
        url: "https://en.yna.co.kr/view/AEN20251203000100320",
        source: "Yonhap",
        country: "KR",
        published_at: new Date(Date.now() - 1000 * 60 * 30).toISOString() // 30 mins ago
    },
    {
        title: "China's Manufacturing PMI Beats Expectations",
        summary: "The Caixin Manufacturing PMI rose to 51.2 in November, signaling a faster-than-anticipated expansion in factory activity.",
        url: "https://www.scmp.com/economy/china-economy/article/3251234/china-pmi",
        source: "SCMP",
        country: "CN",
        published_at: new Date(Date.now() - 1000 * 60 * 45).toISOString() // 45 mins ago
    },
    {
        title: "Nikkei 225 Rebounds on Tech Earnings",
        summary: "Japanese stocks ended higher as semiconductor shares tracked US tech gains, offsetting yen strength.",
        url: "https://asia.nikkei.com/Business/Markets/Nikkei-225",
        source: "Nikkei Asia",
        country: "JP",
        published_at: new Date(Date.now() - 1000 * 60 * 60).toISOString() // 1 hour ago
    }
]

async function seed() {
    console.log('Seeding global_news...')
    const { data, error } = await supabase
        .from('global_news')
        .insert(sampleNews)
        .select()

    if (error) {
        console.error('Error seeding data:', error)
    } else {
        console.log('Successfully seeded', data.length, 'news items.')
    }
}

seed()
