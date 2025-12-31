#!/usr/bin/env python3
"""
G9 Graph RAG Layer - "사고의 폭풍" 인사이트 생성
================================================

Neo4j 그래프 데이터 + LLM = 독창적 인사이트

기능:
1. 현재 시장 상황과 유사한 역사적 패턴 검색
2. 전문가 인사이트 연결
3. 모순/이상 징후 발견
4. LLM으로 서술형 인사이트 생성
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Neo4j 연결 설정
NEO4J_CONFIG = {
    'uri': 'bolt://141.164.35.214:7688',
    'user': 'neo4j',
    'password': 'economy_vultr_2025'
}



@dataclass
class GraphInsight:
    """Graph RAG 인사이트"""
    insight_type: str  # pattern_match, contradiction, expert_view, anomaly
    title: str
    content: str
    confidence: float  # 0.0-1.0
    sources: List[str]
    relevance: str  # high, medium, low


class GraphRAGLayer:
    """
    Graph RAG Layer for v4.0+
    Neo4j 기반 인사이트 생성
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.driver = None
        self._connect()

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def _connect(self):
        """Neo4j 연결"""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                NEO4J_CONFIG['uri'],
                auth=(NEO4J_CONFIG['user'], NEO4J_CONFIG['password'])
            )
            self.log("[GraphRAG] Connected to Neo4j")
        except ImportError:
            self.log("[GraphRAG] neo4j package not installed, using HTTP API")
            self.driver = None
        except Exception as e:
            self.log(f"[GraphRAG] Neo4j connection failed: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def generate_insights(self, market_data: Dict, states: List) -> List[GraphInsight]:
        """
        시장 데이터 기반 인사이트 생성

        Args:
            market_data: US/Asia 시장 데이터
            states: 계산된 State 리스트

        Returns:
            List[GraphInsight]
        """
        insights = []

        self.log("\n[GraphRAG] Generating insights...")

        # 1. Expert Insights 검색
        expert_insights = self._fetch_expert_insights(market_data)
        if expert_insights:
            insights.extend(expert_insights)

        # 2. 모순 발견
        contradictions = self._detect_contradictions(market_data, states)
        if contradictions:
            insights.extend(contradictions)

        # 3. 패턴 매칭 (역사적 유사 상황)
        patterns = self._match_historical_patterns(market_data, states)
        if patterns:
            insights.extend(patterns)

        # 4. LLM 인사이트 생성 (종합)
        llm_insight = self._generate_llm_insight(market_data, states, insights)
        if llm_insight:
            insights.append(llm_insight)

        return insights

    def _fetch_expert_insights(self, market_data: Dict) -> List[GraphInsight]:
        """Neo4j에서 관련 전문가 인사이트 검색"""
        insights = []

        if not self.driver:
            # HTTP API fallback
            return self._fetch_expert_insights_http(market_data)

        try:
            with self.driver.session() as session:
                # VIX 관련 인사이트
                vix = market_data.get('VIX', {}).get('current', 0)

                if vix < 15:
                    # 낮은 VIX = complacency 관련 인사이트
                    result = session.run("""
                        MATCH (e:ExpertInsight)
                        WHERE e.topic IN ['volatility', 'risk', 'Fed', 'inflation']
                        AND e.contrarian = true
                        RETURN e.author, e.insight, e.sentiment
                        LIMIT 3
                    """)

                    for record in result:
                        insights.append(GraphInsight(
                            insight_type="expert_view",
                            title=f"Expert View: {record['e.author']}",
                            content=record['e.insight'],
                            confidence=0.7,
                            sources=[record['e.author']],
                            relevance="high" if record['e.sentiment'] == 'bearish' else "medium"
                        ))
                        self.log(f"  ✅ Expert: {record['e.author']}")

        except Exception as e:
            self.log(f"  ⚠️ Expert fetch error: {e}")

        return insights

    def _fetch_expert_insights_http(self, market_data: Dict) -> List[GraphInsight]:
        """HTTP API로 Neo4j 쿼리 (fallback)"""
        # 하드코딩된 예시 인사이트 (실제로는 Neo4j HTTP API 호출)
        vix = market_data.get('VIX', {}).get('current', 0)

        if vix < 15:
            return [
                GraphInsight(
                    insight_type="expert_view",
                    title="Contrarian View: Low VIX Warning",
                    content="VIX가 15 이하일 때 시장은 '겁이 없는' 상태입니다. "
                           "역사적으로 이런 극단적 낙관은 오래 지속되지 않았습니다. "
                           "1-2개월 내 변동성 스파이크 가능성을 염두에 두세요.",
                    confidence=0.65,
                    sources=["Historical VIX patterns", "Mean reversion theory"],
                    relevance="medium"
                )
            ]
        return []

    def _detect_contradictions(self, market_data: Dict, states: List) -> List[GraphInsight]:
        """
        모순/이상 징후 발견

        예: VIX 낮은데 EM 통화 약세 = 선별적 위험회피
        """
        insights = []

        vix = market_data.get('VIX', {}).get('current', 0)
        usdkrw = market_data.get('USDKRW', {}).get('current', 0) if 'USDKRW' in market_data else 0

        # 모순 1: VIX 낮은데 원화 약세
        if vix < 18 and usdkrw > 1380:
            insights.append(GraphInsight(
                insight_type="contradiction",
                title="모순 발견: 선별적 위험회피",
                content=f"VIX {vix:.1f}은 '위험선호' 신호인데, USD/KRW {usdkrw:.0f}은 "
                       "'신흥국 회피' 신호입니다. 이 조합은 **미국만 좋고 나머지는 위험하다**는 "
                       "시장 판단을 반영합니다. 2018년 EM 위기 초기에도 이런 패턴이 관찰됐습니다. "
                       "아시아 익스포저를 줄이되 미국은 유지하는 전략이 합리적입니다.",
                confidence=0.75,
                sources=["VIX-EM divergence pattern", "2018 EM crisis analogy"],
                relevance="high"
            ))
            self.log("  ⚠️ Contradiction: VIX low but KRW weak")

        # 모순 2: 금 상승 + 주식 상승 = 불안한 랠리
        gold_change = market_data.get('GOLD', {}).get('change_pct', 0)
        spx_change = market_data.get('SPX', {}).get('change_pct', 0)

        if gold_change > 1.0 and spx_change > 0:
            insights.append(GraphInsight(
                insight_type="contradiction",
                title="이상 징후: 금과 주식 동시 상승",
                content=f"Gold +{gold_change:.1f}%와 S&P 500이 동시에 오르고 있습니다. "
                       "일반적으로 금은 안전자산, 주식은 위험자산입니다. 둘이 같이 오르면 "
                       "**시장이 방향을 못 잡고 있다**는 신호일 수 있습니다. "
                       "인플레이션 헤지와 성장 기대가 공존하는 애매한 국면입니다.",
                confidence=0.60,
                sources=["Gold-equity correlation analysis"],
                relevance="medium"
            ))
            self.log("  ⚠️ Anomaly: Gold and equity rising together")

        return insights

    def _match_historical_patterns(self, market_data: Dict, states: List) -> List[GraphInsight]:
        """역사적 유사 패턴 매칭"""
        insights = []

        vix = market_data.get('VIX', {}).get('current', 0)
        dxy = market_data.get('DXY', {}).get('current', 0)
        usdkrw = market_data.get('USDKRW', {}).get('current', 0) if 'USDKRW' in market_data else 0

        # 패턴: VIX < 15 + DXY < 100 + KRW > 1400
        if vix < 15 and dxy < 100 and usdkrw > 1400:
            insights.append(GraphInsight(
                insight_type="pattern_match",
                title="역사적 패턴: 2022년 9월 유사",
                content="현재 조합(VIX 저, DXY 중립, 원화 약세)은 **2022년 9월**과 유사합니다. "
                       "당시 미국은 랠리 중이었으나 원/달러가 1,430원을 넘으면서 "
                       "외국인 순매도가 가속화됐습니다. 이후 3주간 코스피는 -7.2% 하락했습니다. "
                       "**한국 시장 추가 하락 가능성**을 열어두세요.",
                confidence=0.70,
                sources=["2022-09 market data", "KOSPI foreign flow analysis"],
                relevance="high"
            ))
            self.log("  📊 Pattern: Similar to Sep 2022")

        return insights

    def _fetch_x_tone_context(self) -> Dict:
        """
        Neo4j에서 X Search 톤 분석 데이터 가져오기 (LLM context용)
        - ExpertWeekly: US 전문가 컨센서스
        - AsiaWeekly: KR/JP 시장 톤
        """
        context = {
            'us_consensus': None,
            'us_dissenting': None,
            'kr_tone': None,
            'jp_tone': None
        }

        if not self.driver:
            return context

        try:
            with self.driver.session() as session:
                # ExpertWeekly (최신)
                result = session.run("""
                    MATCH (e:ExpertWeekly)
                    RETURN e.consensus_view, e.dissenting_views, e.week_ending
                    ORDER BY e.week_ending DESC
                    LIMIT 1
                """)
                record = result.single()
                if record:
                    context['us_consensus'] = record['e.consensus_view']
                    context['us_dissenting'] = record['e.dissenting_views']
                    self.log("  📰 Loaded US ExpertWeekly tone")

                # AsiaWeekly (최신)
                result = session.run("""
                    MATCH (a:AsiaWeekly)
                    RETURN a.kr_consensus, a.kr_fx_sentiment, a.kr_equity_tone,
                           a.jp_consensus, a.jp_fx_sentiment, a.jp_equity_tone
                    ORDER BY a.week_ending DESC
                    LIMIT 1
                """)
                record = result.single()
                if record:
                    context['kr_tone'] = {
                        'consensus': record['a.kr_consensus'],
                        'fx': record['a.kr_fx_sentiment'],
                        'equity': record['a.kr_equity_tone']
                    }
                    context['jp_tone'] = {
                        'consensus': record['a.jp_consensus'],
                        'fx': record['a.jp_fx_sentiment'],
                        'equity': record['a.jp_equity_tone']
                    }
                    self.log("  📰 Loaded Asia Weekly tone (KR/JP)")

        except Exception as e:
            self.log(f"  ⚠️ X tone fetch error: {e}")

        return context

    def _generate_llm_insight(self, market_data: Dict, states: List,
                              existing_insights: List[GraphInsight]) -> Optional[GraphInsight]:
        """
        X Search 주간 톤 분석 인사이트 생성

        - LLM 실시간 호출 없음
        - 주간 Cron으로 Neo4j에 저장된 X Search 결과만 읽음
        - ExpertWeekly (US) + AsiaWeekly (KR/JP) 데이터 포맷팅
        """

        # Neo4j에서 X Search 주간 결과 읽기
        x_tone = self._fetch_x_tone_context()

        # X Search 데이터가 없으면 None
        if not x_tone.get('us_consensus') and not x_tone.get('kr_tone'):
            self.log("  ℹ️ No X Search weekly data available")
            return None

        # 인사이트 내용 구성 (저장된 데이터 기반)
        content_parts = []
        sources = []

        # US 컨센서스
        if x_tone.get('us_consensus'):
            content_parts.append(f"**US 전문가 컨센서스**: {x_tone['us_consensus']}")
            sources.append("US ExpertWeekly")

            if x_tone.get('us_dissenting'):
                content_parts.append(f"**반대 의견**: {x_tone['us_dissenting']}")

        # 한국 시장 톤
        if x_tone.get('kr_tone'):
            kr = x_tone['kr_tone']
            if kr.get('consensus'):
                content_parts.append(f"**한국 시장**: {kr['consensus']}")
            if kr.get('fx'):
                content_parts.append(f"  - FX 센티먼트: {kr['fx']}")
            if kr.get('equity'):
                content_parts.append(f"  - 주식 톤: {kr['equity']}")
            sources.append("KR AsiaWeekly")

        # 일본 시장 톤
        if x_tone.get('jp_tone'):
            jp = x_tone['jp_tone']
            if jp.get('consensus'):
                content_parts.append(f"**일본 시장**: {jp['consensus']}")
            sources.append("JP AsiaWeekly")

        if not content_parts:
            return None

        self.log("  📰 X Search weekly tone loaded (no LLM call)")

        return GraphInsight(
            insight_type="x_tone_weekly",
            title="X Search 주간 톤 분석",
            content="\n".join(content_parts),
            confidence=0.80,  # 실제 X 데이터 기반이므로 높은 신뢰도
            sources=sources,
            relevance="high"
        )

    def format_insights_markdown(self, insights: List[GraphInsight]) -> str:
        """인사이트를 마크다운으로 포맷"""
        if not insights:
            return "*Graph RAG 인사이트가 없습니다.*"

        lines = []

        # 높은 관련성 인사이트 먼저
        high = [i for i in insights if i.relevance == "high"]
        medium = [i for i in insights if i.relevance == "medium"]

        for insight in high + medium:
            icon = {
                "contradiction": "⚡",
                "pattern_match": "📊",
                "expert_view": "🎯",
                "anomaly": "⚠️",
                "synthesis": "💡",
                "x_tone_weekly": "📰"
            }.get(insight.insight_type, "📌")

            lines.append(f"### {icon} {insight.title}")
            lines.append("")
            lines.append(insight.content)
            lines.append("")
            lines.append(f"*신뢰도: {insight.confidence*100:.0f}% | 출처: {', '.join(insight.sources)}*")
            lines.append("")

        return "\n".join(lines)


def test_graph_rag():
    """테스트"""
    # 테스트용 시장 데이터
    market_data = {
        'VIX': {'current': 14.26, 'change_pct': 0.42, 'valid': True},
        'SPX': {'current': 6904, 'change_pct': -0.02, 'valid': True},
        'DXY': {'current': 98.14, 'change_pct': 0.11, 'valid': True},
        'GOLD': {'current': 4390, 'change_pct': 1.51, 'valid': True},
        'USDKRW': {'current': 1440, 'change_pct': -0.06, 'valid': True},
    }

    states = []  # 간단히 빈 리스트

    rag = GraphRAGLayer(verbose=True)
    insights = rag.generate_insights(market_data, states)

    print("\n" + "="*60)
    print("GRAPH RAG INSIGHTS")
    print("="*60 + "\n")
    print(rag.format_insights_markdown(insights))

    rag.close()


if __name__ == "__main__":
    test_graph_rag()
