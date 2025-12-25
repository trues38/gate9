"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function LandingPage() {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    return (
        <div className="min-h-screen bg-[#050505] text-[#E0E0E0] font-mono selection:bg-[#00FF94] selection:text-black overflow-hidden relative">

            {/* Background Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(20,20,20,0.5)_1px,transparent_1px),linear-gradient(90deg,rgba(20,20,20,0.5)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-0"></div>

            {/* Hero Section */}
            <div className="relative z-10 flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">

                <div className={`transition-all duration-1000 transform ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
                    <div className="inline-block px-3 py-1 mb-6 border border-[#00FF94]/30 rounded-full bg-[#00FF94]/5 text-[#00FF94] text-xs tracking-widest uppercase animate-pulse">
                        ● System Online // V2.0.4
                    </div>

                    <h1 className="text-5xl md:text-7xl font-black text-white tracking-tighter mb-6 leading-tight">
                        REGIME PRO <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00FF94] to-[#00CC7A]">LIVE</span>
                    </h1>

                    <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
                        인공지능이 분석한 <span className="text-white font-bold">전 세계 스포츠 베팅 시장의 흐름</span>을 실시간으로 확인하세요.
                        <br className="hidden md:block" />
                        30년치 역사적 데이터와 현재의 모멘텀을 결합하여, 가장 확실한 <span className="text-[#00FF94]">알파(Alpha)</span>를 찾아냅니다.
                    </p>

                    <div className="flex flex-col md:flex-row gap-4 justify-center items-center">
                        <Link
                            href="/live"
                            className="px-8 py-4 bg-[#00FF94] text-black font-bold text-lg rounded hover:bg-[#00CC7A] transition-all transform hover:scale-105 shadow-[0_0_20px_rgba(0,255,148,0.3)]"
                        >
                            라이브 대시보드 입장 (DEMO)
                        </Link>
                        <button className="px-8 py-4 border border-[#333] hover:border-white text-gray-300 hover:text-white font-bold text-lg rounded transition-colors bg-white/5 backdrop-blur-sm">
                            구독 플랜 보기
                        </button>
                    </div>
                </div>
            </div>

            {/* Feature Grid */}
            <div className="relative z-10 max-w-7xl mx-auto px-6 py-20 border-t border-[#1A1A1A]">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <FeatureCard
                        title="시장 확신도 (Market Conviction)"
                        desc="AI가 209개 활성 레짐을 분석하여 현재 시장의 방향성을 0-100% 점수로 산출합니다."
                        icon="📊"
                    />
                    <FeatureCard
                        title="역사적 DNA 매칭 (Historical Twins)"
                        desc="현재 선수의 퍼포먼스를 과거 전설적인 시즌들과 비교하여 미래 성과를 예측합니다."
                        icon="🧬"
                    />
                    <FeatureCard
                        title="실시간 알파 시그널 (Alpha Signals)"
                        desc="부상, 라인업 변경, 심판 성향 등 모든 변수를 고려하여 가장 확률 높은 기회를 포착합니다."
                        icon="⚡"
                    />
                </div>
            </div>

            {/* Footer */}
            <footer className="relative z-10 py-8 border-t border-[#1A1A1A] text-center text-xs text-gray-600">
                <p>© 2025 REGIME PRO INC. // POWERED BY ANTIGRAVITY ENGINE</p>
            </footer>
        </div>
    );
}

function FeatureCard({ title, desc, icon }: { title: string, desc: string, icon: string }) {
    return (
        <div className="p-8 bg-[#0A0A0A] border border-[#1A1A1A] hover:border-[#00FF94]/50 transition-colors group rounded-xl">
            <div className="text-4xl mb-4 group-hover:scale-110 transition-transform duration-300 inline-block">{icon}</div>
            <h3 className="text-xl font-bold text-white mb-3 group-hover:text-[#00FF94] transition-colors">{title}</h3>
            <p className="text-gray-400 leading-relaxed text-sm">
                {desc}
            </p>
        </div>
    );
}
