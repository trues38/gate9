import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic'; // Disable caching to ensure fresh data

export async function GET() {
    try {
        const supabase = createClient(
            process.env.NEXT_PUBLIC_SUPABASE_URL!,
            process.env.SUPABASE_SERVICE_ROLE_KEY!
        );

        // Fetch latest date from fact_rosters
        const { data: latestDateData } = await supabase
            .from('fact_rosters')
            .select('date')
            .order('date', { ascending: false })
            .limit(1)
            .single();

        const targetDate = latestDateData?.date || new Date().toISOString().split('T')[0];

        // Fetch Rosters for that date
        const { data, error } = await supabase
            .from('fact_rosters')
            .select('*')
            .eq('date', targetDate);

        if (error) throw error;

        // Group by Team ID for Frontend Consumption
        const grouped: Record<number, any[]> = {};
        data?.forEach((row: any) => {
            if (!grouped[row.team_id]) grouped[row.team_id] = [];
            grouped[row.team_id].push({
                name: row.player_name,
                starter: row.is_starter,
                status: row.status,
                last_pts: row.last_pts,
                regime: {
                    label: row.regime_label,
                    momentum: row.momentum_score
                }
            });
        });

        return NextResponse.json(grouped);

    } catch (error) {
        console.error("Roster Fetch Error:", error);
        return NextResponse.json({ error: "Failed to fetch rosters" }, { status: 500 });
    }
}
