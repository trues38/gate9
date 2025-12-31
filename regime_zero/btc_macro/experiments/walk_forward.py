"""
Walk-Forward Validator - OOS 검증 프레임워크

과적합 방지를 위한 체계적 검증:
- Train/Test 분할
- 롤링 윈도우 검증
- 다중 기간 테스트
- OOS 성과 판정
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple
from datetime import datetime, timedelta
import numpy as np

from .metrics import TradeResult, ExperimentMetrics, MetricsCalculator
from .hypothesis import Hypothesis, ValidationCriteria


@dataclass
class ValidationWindow:
    """검증 윈도우"""
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    window_id: int = 0


@dataclass
class WindowResult:
    """윈도우별 결과"""
    window: ValidationWindow
    train_metrics: ExperimentMetrics
    test_metrics: ExperimentMetrics
    passed: bool
    failure_reasons: List[str] = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """Walk-Forward 전체 결과"""
    hypothesis_id: str
    windows: List[WindowResult]

    # 종합 지표
    avg_train_win_rate: float
    avg_test_win_rate: float
    win_rate_decay: float           # Train→Test 승률 하락폭
    test_vs_random: float           # OOS 랜덤 대비 우위
    avg_p_value: float

    # 판정
    overall_passed: bool
    pass_rate: float                # 윈도우 통과율
    verdict: str
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'hypothesis_id': self.hypothesis_id,
            'windows_tested': len(self.windows),
            'pass_rate': f"{self.pass_rate:.0%}",
            'train_win_rate': f"{self.avg_train_win_rate:.1%}",
            'test_win_rate': f"{self.avg_test_win_rate:.1%}",
            'win_rate_decay': f"{self.win_rate_decay:+.1%}",
            'test_vs_random': f"{self.test_vs_random:+.1%}",
            'overall_passed': self.overall_passed,
            'verdict': self.verdict
        }


class WalkForwardValidator:
    """Walk-Forward 검증기"""

    def __init__(self, criteria: ValidationCriteria = None):
        self.criteria = criteria or ValidationCriteria()
        self.metrics_calc = MetricsCalculator()

    def create_windows(self, start_date: str, end_date: str,
                       train_ratio: float = 0.6,
                       n_windows: int = 1) -> List[ValidationWindow]:
        """
        검증 윈도우 생성

        Args:
            start_date: 시작일
            end_date: 종료일
            train_ratio: 훈련 비율 (0.6 = 60% train, 40% test)
            n_windows: 롤링 윈도우 수 (1 = 단순 분할)

        Returns:
            ValidationWindow 리스트
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end - start).days

        if n_windows == 1:
            # 단순 분할
            train_days = int(total_days * train_ratio)
            train_end = start + timedelta(days=train_days)

            return [ValidationWindow(
                train_start=start_date,
                train_end=train_end.strftime('%Y-%m-%d'),
                test_start=(train_end + timedelta(days=1)).strftime('%Y-%m-%d'),
                test_end=end_date,
                window_id=0
            )]

        # 롤링 윈도우
        windows = []
        window_size = total_days // n_windows
        train_size = int(window_size * train_ratio)

        for i in range(n_windows):
            w_start = start + timedelta(days=i * window_size)
            w_train_end = w_start + timedelta(days=train_size)
            w_test_end = w_start + timedelta(days=window_size)

            if w_test_end > end:
                w_test_end = end

            windows.append(ValidationWindow(
                train_start=w_start.strftime('%Y-%m-%d'),
                train_end=w_train_end.strftime('%Y-%m-%d'),
                test_start=(w_train_end + timedelta(days=1)).strftime('%Y-%m-%d'),
                test_end=w_test_end.strftime('%Y-%m-%d'),
                window_id=i
            ))

        return windows

    def validate_window(self, train_trades: List[TradeResult],
                        test_trades: List[TradeResult],
                        window: ValidationWindow) -> WindowResult:
        """
        단일 윈도우 검증

        Args:
            train_trades: 훈련 기간 거래
            test_trades: 테스트 기간 거래
            window: 검증 윈도우

        Returns:
            WindowResult
        """
        # 지표 계산
        train_metrics = self.metrics_calc.calculate(
            train_trades,
            period=f"{window.train_start}~{window.train_end}",
            is_in_sample=True
        )

        test_metrics = self.metrics_calc.calculate(
            test_trades,
            period=f"{window.test_start}~{window.test_end}",
            is_in_sample=False
        )

        # 검증
        passed, reasons = self._check_criteria(train_metrics, test_metrics)

        return WindowResult(
            window=window,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
            passed=passed,
            failure_reasons=reasons
        )

    def _check_criteria(self, train: ExperimentMetrics,
                        test: ExperimentMetrics) -> Tuple[bool, List[str]]:
        """검증 기준 체크"""
        reasons = []
        passed = True

        # 1. OOS 승률 >= 랜덤 + edge
        baseline = 0.5
        required_win_rate = baseline + self.criteria.win_rate_edge

        if test.win_rate < required_win_rate:
            reasons.append(f"OOS win_rate {test.win_rate:.1%} < {required_win_rate:.1%}")
            passed = False

        # 2. 통계적 유의성
        if test.p_value_vs_random > self.criteria.p_value_threshold:
            reasons.append(f"p_value {test.p_value_vs_random:.3f} > {self.criteria.p_value_threshold}")
            passed = False

        # 3. MDD 제한
        if test.max_drawdown > self.criteria.max_drawdown_limit:
            reasons.append(f"MDD {test.max_drawdown:.1%} > {self.criteria.max_drawdown_limit:.1%}")
            passed = False

        # 4. 최소 샘플 수
        if test.total_trades < self.criteria.min_samples:
            reasons.append(f"samples {test.total_trades} < {self.criteria.min_samples}")
            passed = False

        # 5. 과적합 체크 (Train→Test 승률 하락)
        decay = train.win_rate - test.win_rate
        if decay > 0.15:  # 15%p 이상 하락은 과적합 의심
            reasons.append(f"win_rate decay {decay:.1%} (overfitting suspected)")
            passed = False

        return passed, reasons

    def validate(self, hypothesis: Hypothesis,
                 trade_generator: Callable[[str, str, Dict], List[TradeResult]],
                 n_windows: int = 1) -> WalkForwardResult:
        """
        가설 전체 Walk-Forward 검증

        Args:
            hypothesis: 검증할 가설
            trade_generator: 거래 생성 함수 (start, end, conditions) -> trades
            n_windows: 롤링 윈도우 수

        Returns:
            WalkForwardResult
        """
        # 윈도우 생성
        windows = self.create_windows(
            start_date=hypothesis.backtest.start_date,
            end_date=hypothesis.backtest.end_date,
            train_ratio=1 - self.criteria.oos_ratio,
            n_windows=n_windows
        )

        # 각 윈도우 검증
        window_results = []
        for window in windows:
            # 훈련 기간 거래
            train_trades = trade_generator(
                window.train_start,
                window.train_end,
                hypothesis.conditions
            )

            # 테스트 기간 거래
            test_trades = trade_generator(
                window.test_start,
                window.test_end,
                hypothesis.conditions
            )

            result = self.validate_window(train_trades, test_trades, window)
            window_results.append(result)

        # 종합 결과
        return self._aggregate_results(hypothesis.id, window_results)

    def _aggregate_results(self, hypothesis_id: str,
                           window_results: List[WindowResult]) -> WalkForwardResult:
        """윈도우 결과 종합"""
        if not window_results:
            return WalkForwardResult(
                hypothesis_id=hypothesis_id,
                windows=[],
                avg_train_win_rate=0,
                avg_test_win_rate=0,
                win_rate_decay=0,
                test_vs_random=0,
                avg_p_value=1.0,
                overall_passed=False,
                pass_rate=0,
                verdict="NO DATA",
                recommendations=["No validation windows available"]
            )

        # 평균 지표
        train_win_rates = [w.train_metrics.win_rate for w in window_results]
        test_win_rates = [w.test_metrics.win_rate for w in window_results]
        p_values = [w.test_metrics.p_value_vs_random for w in window_results]

        avg_train = np.mean(train_win_rates)
        avg_test = np.mean(test_win_rates)
        decay = avg_train - avg_test
        vs_random = avg_test - 0.5

        # 통과율
        passed_windows = sum(1 for w in window_results if w.passed)
        pass_rate = passed_windows / len(window_results)

        # 전체 통과 기준: 모든 윈도우 통과 또는 80% 이상 통과
        overall_passed = pass_rate >= 0.8

        # 판정 및 권고
        verdict, recommendations = self._generate_verdict(
            avg_train, avg_test, decay, vs_random, pass_rate, window_results
        )

        return WalkForwardResult(
            hypothesis_id=hypothesis_id,
            windows=window_results,
            avg_train_win_rate=avg_train,
            avg_test_win_rate=avg_test,
            win_rate_decay=decay,
            test_vs_random=vs_random,
            avg_p_value=np.mean(p_values),
            overall_passed=overall_passed,
            pass_rate=pass_rate,
            verdict=verdict,
            recommendations=recommendations
        )

    def _generate_verdict(self, avg_train: float, avg_test: float,
                          decay: float, vs_random: float,
                          pass_rate: float,
                          window_results: List[WindowResult]) -> Tuple[str, List[str]]:
        """판정 및 권고 생성"""
        recommendations = []

        if pass_rate >= 0.8 and vs_random >= self.criteria.win_rate_edge:
            verdict = "VALIDATED"
            if decay > 0.05:
                recommendations.append("Minor overfitting detected, consider simplifying")
        elif pass_rate >= 0.5:
            verdict = "MARGINAL"
            recommendations.append("Inconsistent OOS performance across windows")
            if decay > 0.1:
                recommendations.append("Significant overfitting - simplify conditions")
        else:
            verdict = "REJECTED"
            # 실패 원인 분석
            all_reasons = []
            for w in window_results:
                all_reasons.extend(w.failure_reasons)

            if 'overfitting' in ' '.join(all_reasons).lower():
                recommendations.append("Severe overfitting - model too complex")
            if any('p_value' in r for r in all_reasons):
                recommendations.append("Not statistically significant - need more data or simpler rules")
            if any('MDD' in r for r in all_reasons):
                recommendations.append("Risk too high - add position sizing or stop-loss")
            if any('samples' in r for r in all_reasons):
                recommendations.append("Insufficient samples - extend test period or relax conditions")

            if not recommendations:
                recommendations.append("Review hypothesis conditions")

        return verdict, recommendations


class RollingWalkForward:
    """롤링 Walk-Forward (Anchored)"""

    def __init__(self, criteria: ValidationCriteria = None):
        self.criteria = criteria or ValidationCriteria()
        self.validator = WalkForwardValidator(criteria)

    def validate_rolling(self, hypothesis: Hypothesis,
                         trade_generator: Callable,
                         window_months: int = 6,
                         step_months: int = 3) -> Dict[str, WalkForwardResult]:
        """
        롤링 앵커 검증

        시작점은 고정, 테스트 기간만 롤링:
        - Window 1: Train 2020-2021, Test 2022-H1
        - Window 2: Train 2020-2021, Test 2022-H2
        - Window 3: Train 2020-2022, Test 2023-H1
        ...
        """
        results = {}

        start = datetime.strptime(hypothesis.backtest.start_date, '%Y-%m-%d')
        train_end_str = hypothesis.backtest.train_end
        train_end = datetime.strptime(train_end_str, '%Y-%m-%d')
        end = datetime.strptime(hypothesis.backtest.end_date, '%Y-%m-%d')

        # 테스트 기간 롤링
        test_start = train_end + timedelta(days=1)
        window_id = 0

        while test_start < end:
            test_end = min(test_start + timedelta(days=window_months*30), end)

            window = ValidationWindow(
                train_start=hypothesis.backtest.start_date,
                train_end=train_end_str,
                test_start=test_start.strftime('%Y-%m-%d'),
                test_end=test_end.strftime('%Y-%m-%d'),
                window_id=window_id
            )

            # 검증
            train_trades = trade_generator(
                window.train_start, window.train_end, hypothesis.conditions
            )
            test_trades = trade_generator(
                window.test_start, window.test_end, hypothesis.conditions
            )

            result = self.validator.validate_window(train_trades, test_trades, window)
            results[f"window_{window_id}"] = result

            test_start = test_start + timedelta(days=step_months*30)
            window_id += 1

        return results


# 편의 함수
def quick_validate(hypothesis: Hypothesis,
                   trade_generator: Callable) -> WalkForwardResult:
    """빠른 검증 헬퍼"""
    validator = WalkForwardValidator()
    return validator.validate(hypothesis, trade_generator)


def create_simple_split(start: str, end: str,
                        train_ratio: float = 0.6) -> ValidationWindow:
    """단순 분할 헬퍼"""
    validator = WalkForwardValidator()
    windows = validator.create_windows(start, end, train_ratio, n_windows=1)
    return windows[0]
