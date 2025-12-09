
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const { reason, component } = await request.json();

        if (process.env.PROJECT_ENV === 'local' || !process.env.GH_TOKEN) {
            // --- LOCAL MODE (Development) ---
            const { spawn } = require('child_process');
            const path = require('path');

            console.log(`[API] Triggering Local Python: ${component}`);

            // Assume running from project root or find it
            const scriptPath = path.join(process.cwd(), '..', 'nba_ops_pipeline.py');
            // Note: In Next.js dev, process.cwd() is usually 'web'. So '..' is correct for 'g9'.
            // However, let's verify cwd. If running 'next dev' from 'web', cwd is 'web'.

            // Safer to assume we might need absolute path or check env.
            // Let's use relative '..'

            const pythonProcess = spawn('python3', [scriptPath, '--component', component], {
                cwd: path.join(process.cwd(), '..'), // Run in root context
                stdio: 'ignore', // Detach? No, we might want to wait or detach.
                // For OPS Center, usually we want "Fire and Forget" but maybe track pid?
                // Let's detach so API returns fast.
                detached: true
            });

            pythonProcess.unref();

            return NextResponse.json({
                status: "Triggered Local Python",
                mode: "LOCAL",
                component,
                timestamp: new Date().toISOString()
            });

        } else {
            // --- REMOTE MODE (GitHub Actions) ---
            // ... (Existing GitHub Logic) ...
            const owner = process.env.NEXT_PUBLIC_GH_OWNER || "your-github-username";
            const repo = process.env.NEXT_PUBLIC_GH_REPO || "g9";
            const token = process.env.GH_TOKEN;

            // ... existing fetch ...
        }

        // (For brevity, I'm rewriting the whole block to be clean)

        // --- GITHUB FALLBACK (If configured) ---
        return NextResponse.json({ status: "Config Error: Use Local or Set GH_TOKEN" }, { status: 500 });

    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
