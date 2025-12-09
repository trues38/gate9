'use client';

import { createClient } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';

// --- Interfaces ---
interface DebugContext {
    pyscript: string;
    key_check: string;
    infra: string;
    logs: string;
    common_error: string;
}

interface IntegrityItem {
    source: string;
    last_run: string;
    status: 'SUCCESS' | 'WARNING' | 'FAILED' | 'PENDING';
    count: string;
    action: string;
    debug?: DebugContext;
}

interface ErrorLog {
    timestamp: string;
    module: string;
    message: string;
    id: string;
    trace?: string;
}

interface SnapshotItem {
    game: string;
    lineup: string;
    injuries: string;
    referee: string;
    regime: string;
    report: string;
}

interface HealthItem {
    component: string;
    status: 'OK' | 'WARNING' | 'ERROR';
    details: string;
}

interface OpsV2Status {
    v2_enabled: boolean;
    integrity_monitor: IntegrityItem[];
    error_logs: ErrorLog[];
    recentness: Record<string, number>;
    snapshots: SnapshotItem[];
    system_health: HealthItem[];
    reason: string;
}

// --- Components ---

function StatusBadge({ status }: { status: string }) {
    const colors = {
        SUCCESS: 'bg-green-900/40 text-green-400 border-green-800',
        OK: 'bg-green-900/40 text-green-400 border-green-800',
        WARNING: 'bg-amber-900/40 text-amber-400 border-amber-800',
        FAILED: 'bg-red-900/40 text-red-400 border-red-800',
        ERROR: 'bg-red-900/40 text-red-400 border-red-800',
        PENDING: 'bg-slate-800 text-slate-400 border-slate-700',
    };
    const c = colors[status as keyof typeof colors] || colors.PENDING;
    return <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${c}`}>{status}</span>;
}

function DebugModal({ debug, isOpen, onClose }: { debug: DebugContext, isOpen: boolean, onClose: () => void }) {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-lg w-full p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
                <h3 className="text-xl font-bold text-slate-100 mb-4 border-b border-slate-800 pb-2">🛠 Maintenance Cheat Sheet</h3>
                <div className="space-y-4 font-mono text-xs">
                    <div>
                        <span className="text-slate-500 block">PYTHON SCRIPT</span>
                        <span className="text-green-400">{debug.pyscript}</span>
                    </div>
                    <div>
                        <span className="text-slate-500 block">INFRASTRUCTURE</span>
                        <span className="text-indigo-400">{debug.infra}</span>
                    </div>
                    <div>
                        <span className="text-slate-500 block">CRITICAL API KEYS</span>
                        <span className="text-amber-400">{debug.key_check}</span>
                    </div>
                    <div>
                        <span className="text-slate-500 block">LOG FILE</span>
                        <span className="text-slate-300">{debug.logs}</span>
                    </div>
                    <div className="bg-red-900/20 border border-red-900/50 p-3 rounded">
                        <span className="text-red-500 block font-bold">COMMON FAILURE POINT</span>
                        <span className="text-red-300">{debug.common_error}</span>
                    </div>
                </div>
                <button onClick={onClose} className="mt-6 w-full bg-slate-800 hover:bg-slate-700 text-white py-2 rounded transition">Close</button>
            </div>
        </div>
    );
}

function TracebackModal({ error, isOpen, onClose }: { error: ErrorLog, isOpen: boolean, onClose: () => void }) {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="bg-slate-900 border border-red-900/50 rounded-lg max-w-2xl w-full p-6 shadow-2xl border-l-4 border-l-red-500" onClick={e => e.stopPropagation()}>
                <h3 className="text-lg font-bold text-red-500 mb-2">🔥 Traceback / Error Details</h3>
                <div className="text-slate-400 text-sm mb-4">Module: <span className="text-white">{error.module}</span> | Time: {error.timestamp}</div>
                <pre className="bg-black p-4 rounded text-xs font-mono text-red-300 overflow-auto max-h-96 leading-relaxed">
                    {error.trace || "No traceback available."}
                </pre>
                <button onClick={onClose} className="mt-6 w-full bg-red-900/50 hover:bg-red-900 text-white py-2 rounded transition">Close Panel</button>
            </div>
        </div>
    );
}

// --- Main Page ---

export default function OpsCenterPage() {
    const [statusData, setStatusData] = useState<OpsV2Status | null>(null);
    const [loading, setLoading] = useState(true);
    const [debugTarget, setDebugTarget] = useState<DebugContext | null>(null);
    const [traceTarget, setTraceTarget] = useState<ErrorLog | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    // Fetch Status
    const fetchStatus = async () => {
        try {
            setErrorMsg(null);
            const supabase = createClient(
                process.env.NEXT_PUBLIC_SUPABASE_URL!,
                process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
            );
            const { data, error } = await supabase
                .from('admin_system_status')
                .select('*')
                .order('id', { ascending: false })
                .limit(1)
                .single();

            if (error) throw error;

            if (data && data.last_run_log) {
                let parsed;
                if (typeof data.last_run_log === 'string') {
                    try {
                        parsed = JSON.parse(data.last_run_log);
                    } catch (e: any) {
                        setErrorMsg("JSON Parse Failed: " + e.message);
                        return;
                    }
                } else {
                    parsed = data.last_run_log;
                }

                if (parsed && parsed.v2_enabled) {
                    setStatusData(parsed);
                } else {
                    setErrorMsg("Data Missing v2_enabled. Raw: " + JSON.stringify(parsed).substring(0, 100));
                }
            } else {
                setErrorMsg("No Data Received from DB. Row count: " + (data ? "1 (Empty Log)" : "0"));
            }
        } catch (e: any) {
            console.error(e);
            setErrorMsg(e.message || "Unknown Fetch Error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
    }, []);

    // Placeholder actions
    const handleRun = async (component: string) => {
        // alert(`Triggering Payload: ${component}`);
        if (!confirm(`Run Pipeline Component: ${component}?`)) return;

        try {
            const res = await fetch('/api/admin/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ component, reason: 'Manual Admin Trigger' })
            });
            const data = await res.json();
            if (res.ok) {
                alert(`✅ Triggered Successfully!\nMode: ${data.mode || 'Unknown'}\nTimestamp: ${data.timestamp}`);
            } else {
                alert(`❌ Trigger Failed: ${data.error}`);
            }
        } catch (e: any) {
            alert(`❌ Network Error: ${e.message}`);
        }
    };

    if (loading) return <div className="min-h-screen bg-black text-slate-500 flex items-center justify-center font-mono">Loading OPS Center...</div>;
    if (!statusData) return (
        <div className="min-h-screen bg-black text-red-500 p-10 font-mono">
            <h1 className="text-2xl font-bold mb-4">⚠️ OPS Center Loading Failed</h1>
            <p className="mb-4">Status Data could not be loaded.</p>
            <div className="bg-red-900/20 border border-red-900 p-4 rounded text-red-300">
                <strong>Error Details:</strong> {errorMsg || "Waiting for V2 Seed Data..."}
            </div>
            <button onClick={fetchStatus} className="mt-6 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded">Retry Fetch</button>
        </div>
    );

    const { integrity_monitor, error_logs, recentness, snapshots, system_health } = statusData;

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-slate-300 font-sans p-6 pb-20 selection:bg-indigo-900/50">
            {/* Header */}
            <header className="mb-8 flex items-center justify-between border-b border-indigo-900/30 pb-6">
                <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                        SPORTS OPS CENTER <span className="text-xs font-mono text-slate-600 border border-slate-800 px-2 py-0.5 rounded ml-2">V2.0.1</span>
                    </h1>
                    <p className="text-slate-500 text-sm mt-1 font-mono">System Integrity & Factory Pipeline Control</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={fetchStatus} className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded text-xs font-bold transition">
                        ↻ REFRESH
                    </button>
                    <button onClick={() => handleRun('ALL')} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold shadow-lg shadow-indigo-900/50 transition animate-pulse">
                        ▶ RUN PIPELINE
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-12 gap-6">

                {/* LEFT COL: Pipeline & Integrity (8/12) */}
                <div className="col-span-12 lg:col-span-8 space-y-6">

                    {/* 1. Data Integrity Monitor */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
                        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900">
                            <h2 className="font-bold text-slate-200 text-sm tracking-wider flex items-center gap-2">
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                DATA INTEGRITY MONITOR
                            </h2>
                        </div>
                        <table className="w-full text-left text-sm">
                            <thead className="text-xs font-mono text-slate-500 bg-black/20 uppercase">
                                <tr>
                                    <th className="px-6 py-3">Source</th>
                                    <th className="px-6 py-3">Last Run</th>
                                    <th className="px-6 py-3">Status</th>
                                    <th className="px-6 py-3">Volume</th>
                                    <th className="px-6 py-3 text-right">Control</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/50">
                                {integrity_monitor.map((item, idx) => (
                                    <tr key={idx} className="hover:bg-indigo-900/10 transition-colors group">
                                        <td className="px-6 py-3 font-medium text-slate-300 flex items-center gap-2">
                                            {item.source}
                                            {item.debug && (
                                                <button onClick={() => setDebugTarget(item.debug!)} className="opacity-0 group-hover:opacity-100 text-indigo-400 hover:text-indigo-300 transition-opacity">
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                                </button>
                                            )}
                                        </td>
                                        <td className="px-6 py-3 font-mono text-xs text-slate-500">{new Date(item.last_run).toLocaleTimeString()}</td>
                                        <td className="px-6 py-3"><StatusBadge status={item.status} /></td>
                                        <td className="px-6 py-3 text-slate-400">{item.count}</td>
                                        <td className="px-6 py-3 text-right">
                                            <button
                                                onClick={() => handleRun(item.action)}
                                                className="text-[10px] font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1 rounded border border-slate-700 transition"
                                            >
                                                ▶ RUN
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>

                    {/* 5. Latest Snapshots */}
                    <section className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
                        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900">
                            <h2 className="font-bold text-slate-200 text-sm tracking-wider">LATEST SNAPSHOTS (TODAY'S GAMES)</h2>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead className="text-xs font-mono text-slate-500 bg-black/20 uppercase">
                                    <tr>
                                        <th className="px-6 py-3">Matchup</th>
                                        <th className="px-6 py-3">Lineup</th>
                                        <th className="px-6 py-3">Injuries</th>
                                        <th className="px-6 py-3">Referee</th>
                                        <th className="px-6 py-3">Regime</th>
                                        <th className="px-6 py-3 text-right">Report</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                    {snapshots.map((game, idx) => (
                                        <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                                            <td className="px-6 py-3 font-bold text-white">{game.game}</td>
                                            <td className="px-6 py-3 text-slate-400">{game.lineup}</td>
                                            <td className="px-6 py-3 text-slate-400">{game.injuries}</td>
                                            <td className="px-6 py-3 text-slate-400">{game.referee}</td>
                                            <td className="px-6 py-3 text-slate-400">{game.regime}</td>
                                            <td className="px-6 py-3 text-right">
                                                {game.report === 'Retry' ? (
                                                    <button className="text-red-400 text-xs hover:text-red-300 font-bold underline">Retry</button>
                                                ) : <span className="text-green-500 text-xs">{game.report}</span>}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>

                </div>

                {/* RIGHT COL: Status & Health (4/12) */}
                <div className="col-span-12 lg:col-span-4 space-y-6">

                    {/* 4. Recentness Bar */}
                    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                        <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">Pipeline Freshness</h2>
                        <div className="space-y-4">
                            {Object.entries(recentness).map(([key, val]) => (
                                <div key={key}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="capitalize text-slate-400">{key}</span>
                                        <span className={val < 80 ? 'text-amber-500' : 'text-green-500'}>{val}%</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${val < 80 ? 'bg-amber-500' : 'bg-green-500'}`}
                                            style={{ width: `${val}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* 6. System Health */}
                    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                        <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4">System Health</h2>
                        <div className="space-y-3">
                            {system_health.map((h, i) => (
                                <div key={i} className="flex justify-between items-center text-sm border-b border-slate-800/50 pb-2 last:border-0 last:pb-0">
                                    <span className="text-slate-300">{h.component}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-slate-600">{h.details}</span>
                                        <div className={`w-2 h-2 rounded-full ${h.status === 'OK' ? 'bg-green-500' : h.status === 'ERROR' ? 'bg-red-500' : 'bg-amber-500'}`}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* 2. Error Center */}
                    <section className="bg-red-900/10 border border-red-900/30 rounded-xl p-5">
                        <h2 className="text-xs font-bold text-red-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                            🔥 Error Log Center
                            <span className="px-1.5 py-0.5 bg-red-900 text-red-300 rounded-full text-[10px]">{error_logs.length}</span>
                        </h2>
                        <div className="space-y-3">
                            {error_logs.map((err, i) => (
                                <div key={i} className="p-3 bg-black/40 rounded border border-red-900/20 hover:border-red-600/50 transition cursor-pointer group" onClick={() => setTraceTarget(err)}>
                                    <div className="flex justify-between text-[10px] text-zinc-500 mb-1">
                                        <span>{err.timestamp}</span>
                                        <span className="uppercase">{err.module}</span>
                                    </div>
                                    <div className="text-xs text-red-300 truncate font-mono">
                                        {err.message}
                                    </div>
                                    <div className="mt-1 text-[10px] text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity text-right">
                                        View Traceback →
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                </div>
            </div>

            {/* Modals */}
            {debugTarget && <DebugModal debug={debugTarget} isOpen={!!debugTarget} onClose={() => setDebugTarget(null)} />}
            {traceTarget && <TracebackModal error={traceTarget} isOpen={!!traceTarget} onClose={() => setTraceTarget(null)} />}

        </div>
    );
}
