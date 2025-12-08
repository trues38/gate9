
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const { reason } = await request.json();

        // GitHub Repository Dispatch / Workflow Dispatch
        // Using Workflow Dispatch for manual run
        const owner = process.env.NEXT_PUBLIC_GH_OWNER || "your-github-username";
        const repo = process.env.NEXT_PUBLIC_GH_REPO || "g9";
        const token = process.env.GH_TOKEN; // Must be set in Vercel Env Vars

        if (!token) {
            return NextResponse.json({ error: "Server Config Error: Missing GH_TOKEN" }, { status: 500 });
        }

        const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/actions/workflows/nba_automation.yml/dispatches`, {
            method: "POST",
            headers: {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": `token ${token}`,
            },
            body: JSON.stringify({
                ref: "main",
                inputs: {
                    reason: reason || "Dashboard Trigger"
                }
            })
        });

        if (!response.ok) {
            const txt = await response.text();
            return NextResponse.json({ error: "GitHub API Failed", details: txt }, { status: response.status });
        }

        return NextResponse.json({ status: "Triggered Successfully", timestamp: new Date().toISOString() });

    } catch (error) {
        return NextResponse.json({ error: "Internal Error" }, { status: 500 });
    }
}
