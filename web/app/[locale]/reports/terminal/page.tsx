'use client';

import { useState, useEffect } from 'react';

export default function TerminalReportPage() {
    const [report, setReport] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [mode, setMode] = useState<'REPORT' | 'TERMINAL'>('REPORT');

    useEffect(() => {
        async function fetchReport() {
            try {
                const res = await fetch('/api/reports/latest');
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                setReport(data);
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        fetchReport();
    }, []);

    if (loading) return <div className="min-h-screen bg-black text-green-500 font-mono p-10 flex items-center justify-center">INITIALIZING TERMINAL...</div>;
    if (!report) return <div className="min-h-screen bg-black text-red-500 font-mono p-10">NO SIGNAL DETECTED.</div>;

    const metadata = report.metadata || {};
    // Extract HTML content from metadata (it was stored as html_report)
    const htmlContent = metadata.html_report || "<p>No Rendered Report Available</p>";
    // Extract JSON content
    const terminalJson = report.content;

    return (
        <div className="min-h-screen bg-black text-slate-300 font-sans selection:bg-green-900 selection:text-white pb-20">
            {/* Header */}
            <div className="fixed top-0 left-0 right-0 h-14 bg-black/90 backdrop-blur border-b border-green-900/30 flex items-center justify-between px-6 z-50">
                <div className="flex items-center gap-3">
                    <span className="w-3 h-3 bg-green-500 rounded-full animate-pulse shadow-[0_0_10px_#22c55e]"></span>
                    <h1 className="font-mono text-green-500 font-bold tracking-widest text-lg">
                        MATCHUP_TERMINAL_VIEW <span className="text-slate-600 text-xs ml-2">v2.0</span>
                    </h1>
                </div>

                <div className="flex bg-slate-900 rounded-md p-1 border border-slate-800">
                    <button
                        onClick={() => setMode('REPORT')}
                        className={`px-4 py-1 text-xs font-bold rounded transition-all ${mode === 'REPORT' ? 'bg-green-900 text-green-300 shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        PRO_REPORT
                    </button>
                    <button
                        onClick={() => setMode('TERMINAL')}
                        className={`px-4 py-1 text-xs font-bold rounded transition-all ${mode === 'TERMINAL' ? 'bg-amber-900/50 text-amber-500 shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        JSON_LAYER
                    </button>
                    <button
                        onClick={() => window.location.reload()}
                        className="ml-2 px-3 py-1 text-xs font-mono text-slate-500 hover:text-green-400 border-l border-slate-800"
                    >
                        ↻ REFRESH
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="pt-24 max-w-5xl mx-auto px-6">

                {/* Meta Banner */}
                <div className="mb-8 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono border-b border-slate-800 pb-6 uppercase text-slate-500">
                    <div>
                        <span className="block text-slate-700">Sequence ID</span>
                        <span className="text-slate-300">{report.id}</span>
                    </div>
                    <div>
                        <span className="block text-slate-700">Target Date</span>
                        <span className="text-amber-500">{report.date}</span>
                    </div>
                    <div>
                        <span className="block text-slate-700">Pipeline Status</span>
                        <span className="text-green-500">OPERATIONAL</span>
                    </div>
                    <div className="text-right">
                        <span className="block text-slate-700">Generated At</span>
                        <span className="text-slate-300">{new Date(report.created_at).toLocaleTimeString()}</span>
                    </div>
                </div>

                {mode === 'REPORT' ? (
                    <div className="animate-in fade-in duration-500">
                        {/* 
                           We render the HTML unsafely because we trust our own pipeline.
                           In a real app, sanitize this or use a Markdown renderer if the source was MD.
                           Here user requested HTML output from the LLM. 
                        */}
                        <div
                            className="prose prose-invert prose-green max-w-none 
                            prose-headings:font-mono prose-headings:uppercase prose-h1:text-4xl prose-h1:text-white
                            prose-p:text-slate-400 prose-strong:text-amber-500"
                            dangerouslySetInnerHTML={{ __html: htmlContent }}
                        />
                    </div>
                ) : (
                    <div className="animate-in fade-in duration-500">
                        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-x-auto relative group">
                            <div className="absolute top-2 right-2 text-[10px] text-slate-600 font-mono">ROOT_ACCESS: READ_ONLY</div>
                            <pre className="text-xs font-mono text-green-400 leading-relaxed">
                                {JSON.stringify(terminalJson, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
