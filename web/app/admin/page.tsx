
"use client";
import React, { useEffect, useState } from 'react';

// Types for API Response
interface HealthStatus {
    date: string;
    lineups_synced: boolean;
    lineup_player_count: number;
    regime_synced: boolean;
    regime_team_count: number;
    db_status: string;
}

export default function AdminDashboard() {
    const [status, setStatus] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [genLoading, setGenLoading] = useState(false);

    // 1. Fetch Health Status
    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/admin/status');
            if (!res.ok) throw new Error("API Offline");
            const data = await res.json();
            setStatus(data);
        } catch (e) {
            console.error(e);
            setStatus(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        // Poll every 30s
        const interval = setInterval(fetchStatus, 30000);
        return () => clearInterval(interval);
    }, []);

    // 2. Trigger Report Generation
    const handleGenerate = async () => {
        if (!confirm("Start Batch Generation for ALL games?")) return;
        setGenLoading(true);
        try {
            await fetch('/api/admin/trigger', {
                method: 'POST',
                body: JSON.stringify({ reason: "Manual Dashboard Trigger" })
            });
            alert("Batch Job Triggered! Monitor Status Board.");
        } catch (e) {
            alert("Failed to trigger job.");
        } finally {
            setGenLoading(false);
        }
    };

    if (loading) return <div className="p-10 text-white">Loading System Status...</div>;

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
            {/* Header */}
            <header className="mb-10 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-amber-500">NBA 작전 상황실 (OPS CENTER)</h1>
                    <p className="text-slate-400 mt-2 font-mono text-sm">
                        마스터 컨트롤 // 날짜: {status?.date || '알 수 없음'}
                    </p>
                </div>
                <div className="flex gap-4">
                    {status?.db_status === "Healthy" ? (
                        <span className="px-4 py-2 bg-green-900 text-green-300 rounded border border-green-700 font-mono text-sm flex items-center gap-2">
                            ● API 정상 (ONLINE)
                        </span>
                    ) : (
                        <span className="px-4 py-2 bg-red-900 text-red-300 rounded border border-red-700 font-mono text-sm flex items-center gap-2">
                            ● API 오프라인 (OFFLINE)
                        </span>
                    )}
                </div>
            </header>

            {/* Main Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">

                {/* Module 1: Lineup Integrity */}
                <StatusCard
                    title="라인업 무결성"
                    value={status?.lineups_synced ? "동기화 완료" : "오류/구버전"}
                    detail={`${status?.lineup_player_count || 0}명 선수 활성`}
                    isHealthy={!!status?.lineups_synced}
                />

                {/* Module 2: Regime Snapshots */}
                <StatusCard
                    title="레짐 엔진 (Regime)"
                    value={status?.regime_synced ? "정상 작동" : "데이터 없음"}
                    detail={`${status?.regime_team_count || 0}개 팀 감시 중`}
                    isHealthy={!!status?.regime_synced}
                />

                {/* Module 3: Injury Feeds */}
                <StatusCard
                    title="부상자 리포트"
                    value="대기 중"
                    detail="피드 연동 개발 진행 중"
                    isHealthy={false} // Todo
                    isWarning={true}
                />

                {/* Module 4: DuckDB State */}
                <StatusCard
                    title="데이터 레이크 (DuckDB)"
                    value={status?.db_status || "알 수 없음"}
                    detail="nba_analytics.duckdb"
                    isHealthy={status?.db_status === "Healthy"}
                />
            </div>

            {/* Control Panel */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
                    <h2 className="text-xl font-bold mb-4 text-slate-300">⚡ 액션 컨트롤 (Action Controls)</h2>
                    <div className="flex gap-4">
                        <button
                            onClick={handleGenerate}
                            disabled={genLoading}
                            className={`px-6 py-3 rounded font-bold transition-colors ${genLoading
                                ? "bg-slate-600 cursor-not-allowed"
                                : "bg-blue-600 hover:bg-blue-500 text-white"
                                }`}
                        >
                            {genLoading ? "🚀 실행 중..." : "배치(Batch) 생성 시작"}
                        </button>
                    </div>
                </div>

                <OverridePanel />
            </div>

            {/* Raw Data Preview (Snapshot Viewer) */}
            <div className="mt-10">
                <h2 className="text-xl font-bold mb-4 text-slate-300">📋 스냅샷 뷰어 (샘플: Team 21)</h2>
                <RosterPreview teamId={21} />
            </div>

        </div>
    );
}

// Sub-components

function OverridePanel() {
    const [teamId, setTeamId] = useState("21");
    const [player, setPlayer] = useState("Devin Booker");
    const [field, setField] = useState("status");
    const [value, setValue] = useState("OUT");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!confirm(`Force Set ${player} to ${value}?`)) return;

        setLoading(true);
        try {
            await fetch('http://localhost:8000/actions/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entity_type: "PLAYER",
                    entity_id: `${teamId}:${player}`,
                    field,
                    new_value: value,
                    notes: "Manual Override from Dashboard"
                })
            });
            alert("수정 요청 완료! 배치를 다시 실행하면 반영됩니다.");
        } catch (e) {
            alert("수정 요청 실패");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-slate-800 rounded-lg border border-amber-900/50 p-6">
            <h2 className="text-xl font-bold mb-4 text-amber-500">🔧 수동 데이터 수정 (Manual Override)</h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <div className="flex gap-2">
                    <input className="bg-slate-900 border border-slate-700 p-2 rounded text-white flex-1"
                        placeholder="팀 ID (예: 21)" value={teamId} onChange={e => setTeamId(e.target.value)} />
                    <input className="bg-slate-900 border border-slate-700 p-2 rounded text-white flex-[2]"
                        placeholder="선수 이름" value={player} onChange={e => setPlayer(e.target.value)} />
                </div>
                <div className="flex gap-2">
                    <select className="bg-slate-900 border border-slate-700 p-2 rounded text-white flex-1"
                        value={field} onChange={e => setField(e.target.value)}>
                        <option value="status">상태 (Status)</option>
                        <option value="regime">레짐 점수 (Regime Score)</option>
                    </select>
                    <input className="bg-slate-900 border border-slate-700 p-2 rounded text-white flex-[2]"
                        placeholder="새 값 (예: OUT)" value={value} onChange={e => setValue(e.target.value)} />
                </div>
                <button disabled={loading} className="bg-amber-700 hover:bg-amber-600 text-white font-bold py-2 rounded mt-2">
                    {loading ? "적용 중..." : "강제 업데이트 실행"}
                </button>
            </form>
        </div>
    );
}

function StatusCard({ title, value, detail, isHealthy, isWarning }: any) {
    let colorClass = "bg-green-900/20 border-green-800 text-green-400";
    if (isWarning) colorClass = "bg-yellow-900/20 border-yellow-800 text-yellow-400";
    if (!isHealthy && !isWarning) colorClass = "bg-red-900/20 border-red-800 text-red-400";

    return (
        <div className={`p-6 rounded-lg border ${colorClass} flex flex-col`}>
            <h3 className="text-sm font-semibold uppercase opacity-70 mb-2">{title}</h3>
            <div className="text-3xl font-bold mb-1">{value}</div>
            <div className="text-sm opacity-60">{detail}</div>
        </div>
    );
}

function RosterPreview({ teamId }: { teamId: number }) {
    const [data, setData] = useState<any[]>([]);

    useEffect(() => {
        useEffect(() => {
            // Fetch from LIVE SUPABASE API (fact_rosters)
            // This ensures the dashboard reflects the exact state of the pipeline
            fetch('/api/admin/roster')
                .then(r => r.json())
                .then(json => {
                    const teamData = json[teamId] || [];
                    setData(teamData);
                })
                .catch(e => console.log("Roster API Error:", e));
        }, [teamId]);

        if (!data.length) return <div className="text-slate-500 italic">No Roster Data Loaded.</div>;

        return (
            <div className="bg-slate-800 rounded border border-slate-700 overflow-hidden">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-900 text-slate-400 uppercase">
                        <tr>
                            <th className="px-4 py-3">선수명</th>
                            <th className="px-4 py-3">상태</th>
                            <th className="px-4 py-3">최근 득점</th>
                            <th className="px-4 py-3">역할</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700 text-slate-300">
                        {data.map((p, i) => (
                            <tr key={i} className="hover:bg-slate-700/50">
                                <td className="px-4 py-3 font-medium text-white">{p.name}</td>
                                <td className="px-4 py-3 text-green-400">{p.status}</td>
                                <td className="px-4 py-3">{p.last_pts}</td>
                                <td className="px-4 py-3">
                                    {p.starter ? <span className="text-amber-400">선발 (STARTER)</span> : "교체 (Reserve)"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    }
