
"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

export default function AdminDashboard() {
    const t = useTranslations("Index");
    const [output, setOutput] = useState("");
    const [loading, setLoading] = useState(false);
    const [gameId, setGameId] = useState("");

    const runCommand = async (action: string, payload: any = {}) => {
        setLoading(true);
        setOutput(`🚀 Executing ${action}...`);
        try {
            const res = await fetch("/api/admin", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action, payload }),
            });
            const data = await res.json();
            setOutput(JSON.stringify(data, null, 2));
        } catch (e: any) {
            setOutput(`Error: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#050505] text-white p-8 font-mono">
            <header className="mb-12 border-b border-gray-800 pb-4">
                <h1 className="text-4xl font-bold text-[#00FF94] tracking-tighter">
                    REGIME CONTROL CENTER
                </h1>
                <p className="text-gray-500 mt-2">
                    {t("title")} | Status: <span className="text-green-500">ONLINE</span>
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* ACTION PANEL */}
                <div className="space-y-6">
                    <div className="p-6 border border-gray-800 rounded bg-[#0A0A0A]">
                        <h2 className="text-xl font-bold text-white mb-4">Daily Operations</h2>
                        <div className="flex flex-col gap-4">
                            <button
                                onClick={() => runCommand("run_daily")}
                                disabled={loading}
                                className="bg-[#00FF94] text-black font-bold py-3 px-6 rounded hover:bg-green-400 transition-colors disabled:opacity-50"
                            >
                                {loading ? "PROCESSING..." : "▶ RUN DAILY UPDATE (17:00 FREEZE)"}
                            </button>

                            <button
                                onClick={() => runCommand("check_health")}
                                className="bg-gray-800 text-white py-3 px-6 rounded hover:bg-gray-700 transition-colors"
                            >
                                System Health Check
                            </button>
                        </div>
                    </div>

                    <div className="p-6 border border-gray-800 rounded bg-[#0A0A0A]">
                        <h2 className="text-xl font-bold text-white mb-4">Ad-Hoc Tooling</h2>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                placeholder="Game ID (e.g. 2025-12-10_MIA_ORL)"
                                className="bg-black border border-gray-700 text-white p-3 rounded w-full"
                                value={gameId}
                                onChange={(e) => setGameId(e.target.value)}
                            />
                            <button
                                onClick={() => runCommand("run_game", { game_id: gameId })}
                                className="bg-blue-600 text-white px-6 rounded hover:bg-blue-500"
                            >
                                Run
                            </button>
                        </div>
                    </div>
                </div>

                {/* CONSOLE OUTPUT */}
                <div className="p-6 border border-gray-800 rounded bg-black font-mono text-sm h-[600px] overflow-auto">
                    <h2 className="text-gray-500 mb-2 border-b border-gray-900 pb-2">Console Output</h2>
                    <pre className="whitespace-pre-wrap text-green-400">
                        {output || "Waiting for command..."}
                    </pre>
                </div>
            </div>
        </div>
    );
}
