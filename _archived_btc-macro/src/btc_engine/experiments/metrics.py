"""
Metrics - 표준 성과 지표 계산

실험 결과의 객관적 평가를 위한 지표들:
- 기본 지표: 승률, 수익률, MDD
- 리스크 조정 지표: Sharpe, Sortino, Calmar
- 통계 검정: t-test, binomial test
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime


@dataclass
class TradeResult:
    """단일 거래 결과"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    is_win: bool
    hold_days: int
    state_at_entry: str = ""


@dataclass
class ExperimentMetrics:
    """실험 성과 지표"""
    # 기본 지표
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    avg_return: float
    avg_win: float
    avg_loss: float

    # 리스크 지표
    max_drawdown: float
    max_drawdown_duration: int  # 일수
    volatility: float
    downside_volatility: float

    # 리스크 조정 수익
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float

    # 연속성
    max_consecutive_wins: int
    max_consecutive_losses: int

    # 통계 검정
    p_value_vs_random: float    # 랜덤 대비 유의성
    confidence_interval: Tuple[float, float]  # 승률 95% CI

    # 메타
    period: str
    is_in_sample: bool

    def to_dict(self) -> dict:
        return {
            'total_trades': self.total_trades,
            'win_rate': f"{self.win_rate:.1%}",
            'total_return': f"{self.total_return:.1%}",
            'max_drawdown': f"{self.max_drawdown:.1%}",
            'sharpe': f"{self.sharpe_ratio:.2f}",
            'p_value': f"{self.p_value_vs_random:.4f}",
            'period': self.period
        }


class MetricsCalculator:
    """성과 지표 계산기"""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate  # 연간 무위험 수익률

    def calculate(self, trades: List[TradeResult],
                  period: str = "",
                  is_in_sample: bool = True) -> ExperimentMetrics:
        """
        거래 리스트로부터 전체 성과 지표 계산

        Args:
            trades: 거래 결과 리스트
            period: 기간 설명 (e.g., "2020-2022")
            is_in_sample: IS 여부

        Returns:
            ExperimentMetrics
        """
        if not trades:
            return self._empty_metrics(period, is_in_sample)

        # 수익률 배열
        returns = np.array([t.return_pct for t in trades])
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        # 기본 지표
        total_trades = len(trades)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_return = np.prod(1 + returns) - 1
        avg_return = np.mean(returns)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # MDD 계산
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0

        # MDD 지속 기간
        mdd_duration = self._calculate_mdd_duration(drawdowns)

        # 변동성
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
        downside_returns = returns[returns < 0]
        downside_volatility = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0

        # Sharpe Ratio (연율화)
        excess_return = avg_return * 252 - self.risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0

        # Sortino Ratio
        sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0

        # Calmar Ratio
        annual_return = total_return * (252 / sum(t.hold_days for t in trades)) if trades else 0
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

        # Profit Factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # 연속 승패
        max_consec_wins, max_consec_losses = self._calculate_streaks(trades)

        # 통계 검정
        p_value = self._calculate_p_value(winning_trades, total_trades)
        ci = self._calculate_confidence_interval(winning_trades, total_trades)

        return ExperimentMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            avg_return=avg_return,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            max_drawdown_duration=mdd_duration,
            volatility=volatility,
            downside_volatility=downside_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            p_value_vs_random=p_value,
            confidence_interval=ci,
            period=period,
            is_in_sample=is_in_sample
        )

    def _empty_metrics(self, period: str, is_in_sample: bool) -> ExperimentMetrics:
        """빈 결과"""
        return ExperimentMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0, total_return=0, avg_return=0, avg_win=0, avg_loss=0,
            max_drawdown=0, max_drawdown_duration=0,
            volatility=0, downside_volatility=0,
            sharpe_ratio=0, sortino_ratio=0, calmar_ratio=0, profit_factor=0,
            max_consecutive_wins=0, max_consecutive_losses=0,
            p_value_vs_random=1.0, confidence_interval=(0, 0),
            period=period, is_in_sample=is_in_sample
        )

    def _calculate_mdd_duration(self, drawdowns: np.ndarray) -> int:
        """MDD 지속 기간"""
        if len(drawdowns) == 0:
            return 0

        max_duration = 0
        current_duration = 0

        for dd in drawdowns:
            if dd > 0:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_duration

    def _calculate_streaks(self, trades: List[TradeResult]) -> Tuple[int, int]:
        """연속 승패 계산"""
        if not trades:
            return 0, 0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for t in trades:
            if t.is_win:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return max_wins, max_losses

    def _calculate_p_value(self, wins: int, total: int,
                           null_prob: float = 0.5) -> float:
        """
        이항 검정으로 p-value 계산

        H0: 승률 = 50% (랜덤)
        H1: 승률 > 50%
        """
        if total == 0:
            return 1.0

        # 단측 검정 (우측)
        p_value = 1 - stats.binom.cdf(wins - 1, total, null_prob)
        return p_value

    def _calculate_confidence_interval(self, wins: int, total: int,
                                        confidence: float = 0.95) -> Tuple[float, float]:
        """승률의 신뢰구간 계산 (Wilson score interval)"""
        if total == 0:
            return (0.0, 0.0)

        z = stats.norm.ppf((1 + confidence) / 2)
        p = wins / total
        n = total

        denominator = 1 + z**2 / n
        center = (p + z**2 / (2*n)) / denominator
        margin = z * np.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator

        return (max(0, center - margin), min(1, center + margin))

    def compare_to_baseline(self, metrics: ExperimentMetrics,
                           baseline_win_rate: float = 0.5) -> dict:
        """
        베이스라인 대비 성과 비교

        Returns:
            비교 결과 딕셔너리
        """
        edge = metrics.win_rate - baseline_win_rate

        # 효과 크기 (Cohen's h)
        h = 2 * (np.arcsin(np.sqrt(metrics.win_rate)) -
                 np.arcsin(np.sqrt(baseline_win_rate)))

        # 유의성 판정
        is_significant = metrics.p_value_vs_random < 0.1

        return {
            'edge': f"{edge:+.1%}",
            'effect_size': f"{h:.3f}",
            'is_significant': is_significant,
            'interpretation': self._interpret_effect_size(h)
        }

    def _interpret_effect_size(self, h: float) -> str:
        """효과 크기 해석"""
        h = abs(h)
        if h < 0.2:
            return "negligible"
        elif h < 0.5:
            return "small"
        elif h < 0.8:
            return "medium"
        else:
            return "large"


class BootstrapValidator:
    """부트스트랩 검증"""

    def __init__(self, n_bootstrap: int = 1000, random_seed: int = 42):
        self.n_bootstrap = n_bootstrap
        self.random_seed = random_seed
        np.random.seed(random_seed)

    def validate(self, trades: List[TradeResult]) -> dict:
        """
        부트스트랩으로 성과 안정성 검증

        Returns:
            검증 결과
        """
        if len(trades) < 10:
            return {'error': 'Not enough trades for bootstrap'}

        returns = np.array([t.return_pct for t in trades])
        n = len(returns)

        # 부트스트랩 샘플링
        bootstrap_win_rates = []
        bootstrap_returns = []

        for _ in range(self.n_bootstrap):
            sample_idx = np.random.choice(n, size=n, replace=True)
            sample_returns = returns[sample_idx]

            win_rate = np.mean(sample_returns > 0)
            total_return = np.prod(1 + sample_returns) - 1

            bootstrap_win_rates.append(win_rate)
            bootstrap_returns.append(total_return)

        # 결과 분석
        win_rate_ci = np.percentile(bootstrap_win_rates, [2.5, 97.5])
        return_ci = np.percentile(bootstrap_returns, [2.5, 97.5])

        return {
            'win_rate_mean': np.mean(bootstrap_win_rates),
            'win_rate_std': np.std(bootstrap_win_rates),
            'win_rate_ci_95': tuple(win_rate_ci),
            'return_mean': np.mean(bootstrap_returns),
            'return_std': np.std(bootstrap_returns),
            'return_ci_95': tuple(return_ci),
            'stability': 'stable' if np.std(bootstrap_win_rates) < 0.05 else 'unstable'
        }


# 편의 함수
def calculate_metrics(trades: List[TradeResult],
                      period: str = "",
                      is_in_sample: bool = True) -> ExperimentMetrics:
    """지표 계산 헬퍼"""
    calculator = MetricsCalculator()
    return calculator.calculate(trades, period, is_in_sample)


def quick_stats(trades: List[TradeResult]) -> dict:
    """빠른 통계 요약"""
    if not trades:
        return {'trades': 0}

    returns = [t.return_pct for t in trades]
    wins = sum(1 for r in returns if r > 0)

    return {
        'trades': len(trades),
        'win_rate': f"{wins/len(trades):.1%}",
        'total_return': f"{(np.prod([1+r for r in returns])-1)*100:.1f}%",
        'avg_return': f"{np.mean(returns)*100:.2f}%",
        'max_win': f"{max(returns)*100:.1f}%",
        'max_loss': f"{min(returns)*100:.1f}%"
    }
