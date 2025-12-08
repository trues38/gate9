"use client";

import { useEffect, useState } from "react";

interface PlayerCard {
  id: string;
  name: string;
  team: string;
  status: string;
  vector: string;
  momentum_score: number;
  conviction_score: number;
  narrative: string;
}

interface DashboardData {
  market_confidence: number;
  market_mood: string;
  players: PlayerCard[];
  generated_at: string;
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/data/dashboard.json")
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-[#E0E0E0] font-mono p-4 md:p-12 selection:bg-[#00FF94] selection:text-black">

      {/* 1. REPORT HEADER */}
      <header className="border-b-2 border-[#1A1A1A] pb-6 mb-8 flex justify-between items-end">
        <div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tighter text-white mb-2">
            REGIME PRO <span className="text-[#00FF94]">LIVE</span>
          </h1>
          <p className="text-sm text-gray-500 uppercase tracking-widest">
            Global Intelligence Briefing // {data ? new Date(data.generated_at).toLocaleString() : "INITIALIZING..."}
          </p>
        </div>
        <div className="text-right hidden md:block">
          <p className="text-xs text-[#00FF94] animate-pulse">● SYSTEM ONLINE</p>
          <p className="text-xs text-gray-600">REF: {data?.generated_at.split('T')[1].substring(0, 8)}</p>
        </div>
      </header>

      {/* 2. MARKET CONFIDENCE (THE SIGNAL) */}
      <section className="mb-12">
        <h2 className="text-xs font-bold text-gray-500 mb-4 border-l-2 border-[#00FF94] pl-2 uppercase">Layer 3: Market Conviction</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center border border-[#1A1A1A] p-8 bg-[#0A0A0A] relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#00FF94] opacity-5 blur-[100px] pointer-events-none"></div>

          <div className="relative z-10">
            <div className="text-6xl md:text-8xl font-black text-white tracking-tighter">
              {loading ? "--" : data?.market_confidence}<span className="text-2xl text-gray-500">%</span>
            </div>
            <div className="text-xl text-[#00FF94] font-bold mt-2">
              {loading ? "CALCULATING..." : `MARKET MOOD: ${data?.market_mood}`}
            </div>
          </div>
          <div className="text-sm text-gray-400 leading-relaxed border-l border-[#1A1A1A] pl-6 relative z-10">
            <p className="mb-4">
              <strong className="text-white">STRATEGY:</strong>
              {data?.market_confidence && data.market_confidence > 70
                ? " High confidence detected across Alpha Regime assets. Aggressive sizing authorized."
                : " Market signals are mixed. Reduce exposure and target only High-Conviction (90%+) assets."}
            </p>
            <p className="italic text-xs opacity-70">
              "System tracks 209 active regimes vs 30-year historical DNA."
            </p>
          </div>
        </div>
      </section>

      {/* 3. HIGH CONVICTION TABLE */}
      <main>
        <div className="flex justify-between items-end mb-4">
          <h2 className="text-xs font-bold text-gray-500 border-l-2 border-[#00FF94] pl-2 uppercase">High Conviction Opportunities</h2>
          <span className="text-xs text-gray-600">SORTED BY: ALPHA SIGNAL</span>
        </div>

        <div className="overflow-x-auto border border-[#1A1A1A]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#0A0A0A]">
              <tr className="text-xs text-gray-500 border-b border-[#1A1A1A]">
                <th className="py-3 pl-4">ASSET (PLAYER)</th>
                <th className="py-3">REGIME STATUS</th>
                <th className="py-3">HISTORICAL DNA (MATCH)</th>
                <th className="py-3">CONFIDENCE</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="py-12 text-center text-[#00FF94] animate-pulse">DECRYPTING INTELLIGENCE...</td></tr>
              ) : (
                data?.players.slice(0, 10).map((p, i) => (
                  <tr key={p.id} className="border-b border-[#1A1A1A] hover:bg-[#111] transition-colors group">
                    <td className="py-4 pl-4">
                      <div className="font-bold text-white text-lg leading-tight">{p.name}</div>
                      <div className="text-xs text-gray-600 font-mono mt-1">{p.team}</div>
                    </td>
                    <td className="py-4">
                      <span className={`px-2 py-1 text-xs font-bold rounded border ${getStatusClass(p.status)}`}>
                        {p.status}
                      </span>
                      <div className="text-[10px] text-gray-500 mt-2 max-w-[150px] leading-tight opacity-0 group-hover:opacity-100 transition-opacity">
                        {p.narrative.split('.')[0]}
                      </div>
                    </td>
                    <td className="py-4 text-xs font-mono text-gray-300">
                      {p.narrative.includes("DNA Match: None") ? (
                        <span className="text-gray-600">--</span>
                      ) : (
                        <span className="text-[#00FF94]">{p.narrative.split("DNA Match: ")[1] || "--"}</span>
                      )}
                    </td>
                    <td className="py-4 pr-4">
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-1.5 bg-[#1A1A1A] rounded-full overflow-hidden">
                          <div
                            className={`h-full ${p.conviction_score > 80 ? 'bg-[#00FF94]' : 'bg-[#7000FF]'}`}
                            style={{ width: `${p.conviction_score}%` }}
                          />
                        </div>
                        <span className="text-lg font-black">{p.conviction_score}</span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-8 text-center">
          <button className="text-xs text-gray-500 hover:text-white transition-colors border-b border-transparent hover:border-white pb-1">
            VIEW FULL ROSTER (209 ASSETS)
          </button>
        </div>
      </main>

      {/* 4. FOOTER */}
      <footer className="mt-16 border-t border-[#1A1A1A] pt-8 flex flex-col md:flex-row justify-between text-xs text-gray-600">
        <p>© 2025 REGIME PRO INC. // POWERED BY ANTIGRAVITY ENGINE</p>
        <p className="mt-2 md:mt-0 font-mono">CONFIDENTIAL BRIEFING</p>
      </footer>
    </div>
  );
}

// Helpers
function getStatusClass(status: string) {
  if (status.includes("Surging")) return "text-[#00FF94] bg-[#00FF94]/5 border-[#00FF94]/20";
  if (status.includes("Slumping")) return "text-[#FF0055] bg-[#FF0055]/5 border-[#FF0055]/20";
  if (status.includes("Stable")) return "text-gray-400 bg-gray-800/50 border-gray-700";
  return "text-[#7000FF] bg-[#7000FF]/5 border-[#7000FF]/20";
}
