"""
META-LAYER: Law Health Monitor & Regime Drift Detector

"언제 이 Law가 죽는가"를 감지하는 레이어

1. Law Health Monitor
   - 최근 N회 WR
   - TP/SL 비율 변화
   - 평균 홀드 기간 변화
   - IBIT Vol 반응 강도 변화

2. Regime Drift Detector
   - ETF 순유입 구조 변화
   - BTC vs ETF 괴리
   - 하락 시 거래량 패턴 변화

3. Capital Deployment Signal
   - 평소: 현금/단기채
   - 신호 시: 30-50% 단발 투입
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "HEALTHY"       # 정상 작동
    WARNING = "WARNING"       # 주의 필요
    CRITICAL = "CRITICAL"     # 심각한 문제
    DEAD = "DEAD"            # Law 무효화


@dataclass
class LawHealthMetrics:
    """Law 건강 지표"""
    timestamp: str

    # Rolling performance
    recent_trades: int
    recent_wr: float
    recent_avg_return: float

    # TP/SL ratio
    tp_count: int
    sl_count: int
    time_count: int
    tp_sl_ratio: float

    # Hold time
    avg_hold_days: float
    hold_days_trend: str  # 'stable', 'increasing', 'decreasing'

    # Signal quality
    avg_vol_ratio: float
    vol_ratio_trend: str
    avg_btc_down: float

    # Final status
    health_status: str
    health_score: float  # 0-100
    warnings: List[str]


@dataclass
class RegimeDriftMetrics:
    """Regime 변화 감지 지표"""
    timestamp: str

    # ETF structure
    ibit_vol_trend: str  # 'growing', 'stable', 'declining'
    ibit_vol_ma30_vs_ma90: float

    # BTC-ETF correlation
    btc_ibit_corr_30d: float
    btc_ibit_corr_90d: float
    corr_drift: float

    # Volume pattern on down days
    down_day_vol_ratio: float
    up_day_vol_ratio: float
    vol_asymmetry: float

    # Drift detection
    drift_detected: bool
    drift_signals: List[str]


@dataclass
class CapitalDeploymentSignal:
    """자본 배치 신호"""
    timestamp: str

    law_active: bool
    law_health: str
    regime_stable: bool

    deployment_signal: str  # 'DEPLOY', 'STANDBY', 'REDUCE', 'EXIT'
    recommended_size: float
    confidence: float

    reasoning: List[str]


class LawHealthMonitor:
    """Law 건강 모니터"""

    # 기준값들
    HEALTHY_WR_MIN = 0.55
    WARNING_WR_MIN = 0.45
    HEALTHY_TP_SL_RATIO = 1.5
    MAX_HEALTHY_HOLD_DAYS = 8

    def __init__(self, trade_history_path: str = None):
        self.trade_history_path = trade_history_path or \
            str(Path(__file__).parent.parent.parent.parent / "logs" / "trade_history.json")
        self.trade_history = self._load_trade_history()

    def _load_trade_history(self) -> List[Dict]:
        """거래 이력 로드"""
        path = Path(self.trade_history_path)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def add_trade(self, trade: Dict):
        """거래 추가"""
        self.trade_history.append(trade)
        self._save_trade_history()

    def _save_trade_history(self):
        """거래 이력 저장"""
        path = Path(self.trade_history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.trade_history, f, indent=2)

    def calculate_health(self, n_recent: int = 5) -> LawHealthMetrics:
        """최근 N회 기준 Law 건강도 계산"""

        if len(self.trade_history) < n_recent:
            # 데이터 부족 시 시뮬레이션 데이터 사용
            trades = self._get_simulated_trades()
        else:
            trades = self.trade_history[-n_recent:]

        if not trades:
            return self._empty_health_metrics()

        # 기본 통계
        wins = sum(1 for t in trades if t.get('win', t.get('return', 0) > 0))
        returns = [t.get('return', t.get('raw_return', 0)) for t in trades]

        # TP/SL 카운트
        tp_count = sum(1 for t in trades if t.get('reason') == 'TP')
        sl_count = sum(1 for t in trades if t.get('reason') == 'SL')
        time_count = sum(1 for t in trades if t.get('reason') == 'Time')

        tp_sl_ratio = tp_count / sl_count if sl_count > 0 else float('inf')

        # 홀드 기간
        hold_days = []
        for t in trades:
            if 'entry_date' in t and 'exit_date' in t:
                try:
                    entry = pd.Timestamp(t['entry_date'])
                    exit = pd.Timestamp(t['exit_date'])
                    hold_days.append((exit - entry).days)
                except:
                    pass

        avg_hold = np.mean(hold_days) if hold_days else 5

        # Vol ratio (신호 품질)
        vol_ratios = [t.get('vol_ratio', t.get('ibit_vol_ratio', 1.5)) for t in trades]
        btc_downs = [t.get('btc_down', t.get('btc_ret_1d', -0.03)) for t in trades]

        # 트렌드 분석
        if len(hold_days) >= 3:
            recent_avg = np.mean(hold_days[-3:])
            older_avg = np.mean(hold_days[:-3]) if len(hold_days) > 3 else recent_avg
            if recent_avg > older_avg * 1.2:
                hold_trend = 'increasing'
            elif recent_avg < older_avg * 0.8:
                hold_trend = 'decreasing'
            else:
                hold_trend = 'stable'
        else:
            hold_trend = 'stable'

        # Vol ratio 트렌드
        if len(vol_ratios) >= 3:
            recent_vol = np.mean(vol_ratios[-3:])
            older_vol = np.mean(vol_ratios[:-3]) if len(vol_ratios) > 3 else recent_vol
            if recent_vol < older_vol * 0.8:
                vol_trend = 'declining'
            elif recent_vol > older_vol * 1.2:
                vol_trend = 'increasing'
            else:
                vol_trend = 'stable'
        else:
            vol_trend = 'stable'

        # 건강 점수 계산
        health_score = 0
        warnings = []

        wr = wins / len(trades)
        avg_ret = np.mean(returns)

        # WR 점수 (40점)
        if wr >= self.HEALTHY_WR_MIN:
            health_score += 40
        elif wr >= self.WARNING_WR_MIN:
            health_score += 20
            warnings.append(f"WR 하락 경고: {wr:.0%}")
        else:
            warnings.append(f"WR 심각: {wr:.0%}")

        # TP/SL 비율 점수 (30점)
        if tp_sl_ratio >= self.HEALTHY_TP_SL_RATIO:
            health_score += 30
        elif tp_sl_ratio >= 1.0:
            health_score += 15
            warnings.append(f"TP/SL 비율 하락: {tp_sl_ratio:.1f}")
        else:
            warnings.append(f"TP/SL 비율 역전: {tp_sl_ratio:.1f}")

        # 홀드 기간 점수 (15점)
        if avg_hold <= self.MAX_HEALTHY_HOLD_DAYS:
            health_score += 15
        else:
            health_score += 5
            warnings.append(f"평균 홀드 기간 증가: {avg_hold:.1f}일")

        # 트렌드 점수 (15점)
        if vol_trend != 'declining':
            health_score += 10
        else:
            warnings.append("IBIT Vol 반응 강도 약화")

        if hold_trend != 'increasing':
            health_score += 5

        # 상태 결정
        if health_score >= 80:
            status = HealthStatus.HEALTHY
        elif health_score >= 50:
            status = HealthStatus.WARNING
        elif health_score >= 25:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.DEAD

        return LawHealthMetrics(
            timestamp=datetime.now().isoformat(),
            recent_trades=len(trades),
            recent_wr=wr,
            recent_avg_return=avg_ret,
            tp_count=tp_count,
            sl_count=sl_count,
            time_count=time_count,
            tp_sl_ratio=tp_sl_ratio,
            avg_hold_days=avg_hold,
            hold_days_trend=hold_trend,
            avg_vol_ratio=np.mean(vol_ratios),
            vol_ratio_trend=vol_trend,
            avg_btc_down=np.mean(btc_downs),
            health_status=status.value,
            health_score=health_score,
            warnings=warnings
        )

    def _get_simulated_trades(self) -> List[Dict]:
        """2024 실제 거래 데이터 시뮬레이션"""
        return [
            {'entry_date': '2024-03-01', 'exit_date': '2024-03-04', 'return': 0.117, 'reason': 'TP', 'vol_ratio': 1.6, 'btc_down': -0.021},
            {'entry_date': '2024-03-06', 'exit_date': '2024-03-08', 'return': 0.071, 'reason': 'TP', 'vol_ratio': 2.2, 'btc_down': -0.066},
            {'entry_date': '2024-03-15', 'exit_date': '2024-03-18', 'return': -0.054, 'reason': 'SL', 'vol_ratio': 1.4, 'btc_down': -0.023},
            {'entry_date': '2024-04-13', 'exit_date': '2024-04-15', 'return': -0.056, 'reason': 'SL', 'vol_ratio': 1.5, 'btc_down': -0.041},
            {'entry_date': '2024-05-01', 'exit_date': '2024-05-14', 'return': 0.015, 'reason': 'Time', 'vol_ratio': 1.3, 'btc_down': -0.050},
            {'entry_date': '2024-06-25', 'exit_date': '2024-07-05', 'return': -0.060, 'reason': 'SL', 'vol_ratio': 1.9, 'btc_down': -0.060},
            {'entry_date': '2024-08-06', 'exit_date': '2024-08-08', 'return': 0.143, 'reason': 'TP', 'vol_ratio': 2.7, 'btc_down': -0.121},
            {'entry_date': '2024-09-07', 'exit_date': '2024-09-12', 'return': 0.077, 'reason': 'TP', 'vol_ratio': 1.5, 'btc_down': -0.039},
            {'entry_date': '2024-10-02', 'exit_date': '2024-10-14', 'return': 0.086, 'reason': 'TP', 'vol_ratio': 1.7, 'btc_down': -0.039},
            {'entry_date': '2024-10-26', 'exit_date': '2024-10-29', 'return': 0.091, 'reason': 'TP', 'vol_ratio': 1.5, 'btc_down': -0.022},
            {'entry_date': '2024-12-06', 'exit_date': '2024-12-16', 'return': 0.098, 'reason': 'TP', 'vol_ratio': 1.4, 'btc_down': -0.022},
        ]

    def _empty_health_metrics(self) -> LawHealthMetrics:
        return LawHealthMetrics(
            timestamp=datetime.now().isoformat(),
            recent_trades=0,
            recent_wr=0,
            recent_avg_return=0,
            tp_count=0,
            sl_count=0,
            time_count=0,
            tp_sl_ratio=0,
            avg_hold_days=0,
            hold_days_trend='unknown',
            avg_vol_ratio=0,
            vol_ratio_trend='unknown',
            avg_btc_down=0,
            health_status=HealthStatus.CRITICAL.value,
            health_score=0,
            warnings=['데이터 부족']
        )


class RegimeDriftDetector:
    """Regime 변화 감지기"""

    def __init__(self):
        pass

    def detect_drift(self) -> RegimeDriftMetrics:
        """Regime 변화 감지"""

        # 데이터 로드
        btc = yf.download('BTC-USD', period='120d', progress=False)
        ibit = yf.download('IBIT', period='120d', progress=False)

        for d in [btc, ibit]:
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)

        # 공통 인덱스
        common_idx = btc.index.intersection(ibit.index)
        btc = btc.reindex(common_idx)
        ibit = ibit.reindex(common_idx)

        drift_signals = []

        # 1. IBIT Volume Trend
        ibit_vol_ma30 = ibit['Volume'].rolling(30).mean().iloc[-1]
        ibit_vol_ma90 = ibit['Volume'].rolling(90).mean().iloc[-1] if len(ibit) >= 90 else ibit_vol_ma30
        vol_ratio = ibit_vol_ma30 / ibit_vol_ma90 if ibit_vol_ma90 > 0 else 1

        if vol_ratio > 1.2:
            ibit_vol_trend = 'growing'
        elif vol_ratio < 0.8:
            ibit_vol_trend = 'declining'
            drift_signals.append("IBIT 거래량 감소 추세")
        else:
            ibit_vol_trend = 'stable'

        # 2. BTC-IBIT Correlation
        btc_ret = btc['Close'].pct_change()
        ibit_ret = ibit['Close'].pct_change()

        corr_30d = btc_ret.tail(30).corr(ibit_ret.tail(30))
        corr_90d = btc_ret.tail(90).corr(ibit_ret.tail(90)) if len(btc_ret) >= 90 else corr_30d

        corr_drift = corr_30d - corr_90d

        if corr_drift < -0.1:
            drift_signals.append(f"BTC-IBIT 상관관계 약화: {corr_drift:.2f}")

        # 3. Volume Asymmetry (하락일 vs 상승일)
        df = pd.DataFrame({
            'btc_ret': btc_ret,
            'ibit_vol': ibit['Volume']
        }).dropna()

        down_days = df[df['btc_ret'] < -0.01]
        up_days = df[df['btc_ret'] > 0.01]

        down_day_vol = down_days['ibit_vol'].mean() if len(down_days) > 0 else 0
        up_day_vol = up_days['ibit_vol'].mean() if len(up_days) > 0 else 0
        overall_vol = df['ibit_vol'].mean()

        down_ratio = down_day_vol / overall_vol if overall_vol > 0 else 1
        up_ratio = up_day_vol / overall_vol if overall_vol > 0 else 1
        vol_asymmetry = down_ratio - up_ratio

        if vol_asymmetry < -0.2:
            drift_signals.append("하락일 ETF 매수세 약화")

        # Drift 판정
        drift_detected = len(drift_signals) >= 2

        return RegimeDriftMetrics(
            timestamp=datetime.now().isoformat(),
            ibit_vol_trend=ibit_vol_trend,
            ibit_vol_ma30_vs_ma90=vol_ratio,
            btc_ibit_corr_30d=corr_30d,
            btc_ibit_corr_90d=corr_90d,
            corr_drift=corr_drift,
            down_day_vol_ratio=down_ratio,
            up_day_vol_ratio=up_ratio,
            vol_asymmetry=vol_asymmetry,
            drift_detected=drift_detected,
            drift_signals=drift_signals
        )


class CapitalDeploymentEngine:
    """자본 배치 엔진"""

    def __init__(self):
        self.health_monitor = LawHealthMonitor()
        self.drift_detector = RegimeDriftDetector()

    def get_deployment_signal(self, law_active: bool) -> CapitalDeploymentSignal:
        """자본 배치 신호 생성"""

        health = self.health_monitor.calculate_health()
        drift = self.drift_detector.detect_drift()

        reasoning = []

        # 기본 상태
        regime_stable = not drift.drift_detected

        # 배치 결정
        if not law_active:
            signal = 'STANDBY'
            size = 0.0
            confidence = 1.0
            reasoning.append("Law 신호 없음 - 현금/단기채 유지")

        elif health.health_status == 'DEAD':
            signal = 'EXIT'
            size = 0.0
            confidence = 0.9
            reasoning.append("Law 무효화 감지 - 전략 중단")

        elif health.health_status == 'CRITICAL':
            signal = 'REDUCE'
            size = 0.15
            confidence = 0.6
            reasoning.append(f"Law 건강 심각: Score={health.health_score}")
            reasoning.extend(health.warnings)

        elif drift.drift_detected:
            signal = 'REDUCE'
            size = 0.20
            confidence = 0.7
            reasoning.append("Regime 변화 감지")
            reasoning.extend(drift.drift_signals)

        elif health.health_status == 'WARNING':
            signal = 'DEPLOY'
            size = 0.30
            confidence = 0.75
            reasoning.append(f"Law 건강 주의: Score={health.health_score}")
            reasoning.append("보수적 배치")

        else:  # HEALTHY
            signal = 'DEPLOY'
            size = 0.50
            confidence = 0.9
            reasoning.append(f"Law 건강: Score={health.health_score}")
            reasoning.append("적극적 배치 가능")

        return CapitalDeploymentSignal(
            timestamp=datetime.now().isoformat(),
            law_active=law_active,
            law_health=health.health_status,
            regime_stable=regime_stable,
            deployment_signal=signal,
            recommended_size=size,
            confidence=confidence,
            reasoning=reasoning
        )


def print_full_status():
    """전체 상태 출력"""

    print("=" * 70)
    print("META-LAYER STATUS REPORT")
    print("=" * 70)

    # Health Monitor
    monitor = LawHealthMonitor()
    health = monitor.calculate_health()

    print("\n[1] LAW HEALTH MONITOR")
    print("-" * 50)
    print(f"Status: {health.health_status} (Score: {health.health_score}/100)")
    print(f"Recent {health.recent_trades} trades: WR={health.recent_wr:.0%}, Avg R={health.recent_avg_return*100:+.1f}%")
    print(f"TP/SL Ratio: {health.tp_sl_ratio:.1f}x (TP:{health.tp_count}, SL:{health.sl_count}, Time:{health.time_count})")
    print(f"Avg Hold: {health.avg_hold_days:.1f} days ({health.hold_days_trend})")
    print(f"Vol Ratio: {health.avg_vol_ratio:.2f}x ({health.vol_ratio_trend})")

    if health.warnings:
        print("\n⚠️ Warnings:")
        for w in health.warnings:
            print(f"  - {w}")

    # Regime Drift
    detector = RegimeDriftDetector()
    drift = detector.detect_drift()

    print("\n[2] REGIME DRIFT DETECTOR")
    print("-" * 50)
    print(f"IBIT Vol Trend: {drift.ibit_vol_trend} (30d/90d: {drift.ibit_vol_ma30_vs_ma90:.2f}x)")
    print(f"BTC-IBIT Corr: 30d={drift.btc_ibit_corr_30d:.2f}, 90d={drift.btc_ibit_corr_90d:.2f}")
    print(f"Vol Asymmetry: {drift.vol_asymmetry:+.2f} (Down:{drift.down_day_vol_ratio:.2f}x, Up:{drift.up_day_vol_ratio:.2f}x)")

    if drift.drift_detected:
        print("\n🚨 DRIFT DETECTED:")
        for s in drift.drift_signals:
            print(f"  - {s}")
    else:
        print("\n✅ No significant drift detected")

    # Capital Deployment
    engine = CapitalDeploymentEngine()

    print("\n[3] CAPITAL DEPLOYMENT SIGNAL")
    print("-" * 50)

    # 신호 없을 때
    deploy_inactive = engine.get_deployment_signal(law_active=False)
    print(f"If Law INACTIVE: {deploy_inactive.deployment_signal} (Size: {deploy_inactive.recommended_size:.0%})")

    # 신호 있을 때
    deploy_active = engine.get_deployment_signal(law_active=True)
    print(f"If Law ACTIVE:   {deploy_active.deployment_signal} (Size: {deploy_active.recommended_size:.0%})")
    print(f"Confidence: {deploy_active.confidence:.0%}")

    print("\nReasoning:")
    for r in deploy_active.reasoning:
        print(f"  • {r}")

    print("\n" + "=" * 70)


def main():
    print_full_status()


if __name__ == "__main__":
    main()
