
import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase Client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!; // Must use Service Role for writing without auth if admin

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { entity_type, entity_id, field, new_value, notes } = body;

        if (!supabaseUrl || !supabaseKey) {
            return NextResponse.json({ error: "Server Config Error: Missing Supabase Keys" }, { status: 500 });
        }

        const supabase = createClient(supabaseUrl, supabaseKey);

        const { data, error } = await supabase
            .from('ops_overrides')
            .insert([
                {
                    target_date: new Date().toISOString(),
                    entity_type,
                    entity_id,
                    field,
                    new_value,
                    notes: notes || "Dashboard API"
                }
            ])
            .select();

        if (error) {
            return NextResponse.json({ error: error.message }, { status: 400 });
        }

        return NextResponse.json({ status: "Override Saved", data });

    } catch (error) {
        return NextResponse.json({ error: "Internal Error" }, { status: 500 });
    }
}
