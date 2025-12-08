
import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export async function GET() {
    try {
        if (!supabaseUrl || !supabaseKey) {
            // Fallback or Error
            return NextResponse.json({ db_status: "Config Missing" });
        }

        const supabase = createClient(supabaseUrl, supabaseKey);

        // Fetch latest status
        const { data, error } = await supabase
            .from('admin_system_status')
            .select('*')
            .order('updated_at', { ascending: false })
            .limit(1)
            .single();

        if (error || !data) {
            return NextResponse.json({
                date: new Date().toISOString().split('T')[0],
                db_status: "Supabase Connected (No Logs)"
            });
        }

        const logs = data.last_run_log ? JSON.parse(data.last_run_log) : {};

        return NextResponse.json({
            date: data.updated_at,
            lineups_synced: data.lineups_updated,
            lineup_player_count: data.processed_count, // heuristic
            regime_synced: data.regimes_updated,
            db_status: data.last_run_status || "Unknown",
            logs: logs
        });

    } catch (error) {
        return NextResponse.json({ db_status: "Error" });
    }
}
