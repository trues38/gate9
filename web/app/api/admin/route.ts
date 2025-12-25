
import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: Request) {
    try {
        const { action, payload } = await request.json();

        // Validate Action
        const validActions = ['run_daily', 'run_game', 'check_health', 'freeze_snapshot'];
        if (!validActions.includes(action)) {
            return NextResponse.json({ error: 'Invalid Action' }, { status: 400 });
        }

        // Call Python Script (admin_bridge.py)
        // Script is in /Users/js/g9/nba_data/admin_bridge.py
        // We assume 'python3' is available.
        // In Production (Vercel), this won't work easily without a server. 
        // But for this LOCAL Ops Center (Mac), it works fine.

        const cmd = `python3 ../nba_data/admin_bridge.py --action ${action} --payload '${JSON.stringify(payload || {})}'`;
        console.log(`Executing: ${cmd}`);

        const { stdout, stderr } = await execAsync(cmd, { cwd: process.cwd() }); // CWD is usually project root (web)

        if (stderr) console.error("STDERR:", stderr);

        // Parse output if it's JSON, else return text
        try {
            const jsonOutput = JSON.parse(stdout);
            return NextResponse.json(jsonOutput);
        } catch {
            return NextResponse.json({ result: stdout, raw: true });
        }

    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
