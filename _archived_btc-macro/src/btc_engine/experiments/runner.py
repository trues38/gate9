"""
Experiment Runner - 가설 실험 실행기

가설 기반 실험의 전체 파이프라인:
1. 가설 로드
2. 거래 생성
3. Walk-Forward 검증
4. 결과 저장

Core 엔진과 분리된 실험 레이어의 진입점
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
import yaml

from .hypothesis import (
    Hypothesis, HypothesisLoader, HypothesisStatus,
    ConditionEvaluator, ValidationCriteria
)
from .metrics import TradeResult, ExperimentMetrics, MetricsCalculator, quick_stats
from .walk_forward import WalkForwardValidator, WalkForwardResult


@dataclass
class ExperimentConfig:
    """실험 설정"""
    hypothesis_id: str
    run_walk_forward: bool = True
    n_windows: int = 1
    save_results: bool = True
    output_dir: str = "data/experiments"
    verbose: bool = True


@dataclass
class ExperimentReport:
    """실험 결과 리포트"""
    hypothesis_id: str
    hypothesis_name: str
    run_at: str
    config: ExperimentConfig

    # 결과
    total_trades: int
    in_sample_metrics: Optional[ExperimentMetrics]
    out_of_sample_metrics: Optional[ExperimentMetrics]
    walk_forward_result: Optional[WalkForwardResult]

    # 판정
    verdict: str
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            'hypothesis_id': self.hypothesis_id,
            'hypothesis_name': self.hypothesis_name,
            'run_at': self.run_at,
            'total_trades': self.total_trades,
            'verdict': self.verdict,
            'recommendations': self.recommendations,
            'in_sample': self.in_sample_metrics.to_dict() if self.in_sample_metrics else None,
            'out_of_sample': self.out_of_sample_metrics.to_dict() if self.out_of_sample_metrics else None,
            'walk_forward': self.walk_forward_result.to_dict() if self.walk_forward_result else None
        }

    def summary(self) -> str:
        """요약 문자열"""
        lines = [
            f"=== {self.hypothesis_name} ===",
            f"ID: {self.hypothesis_id}",
            f"Run: {self.run_at}",
            f"Trades: {self.total_trades}",
            "",
            f"Verdict: {self.verdict}",
        ]

        if self.in_sample_metrics:
            lines.append(f"IS Win Rate: {self.in_sample_metrics.win_rate:.1%}")
        if self.out_of_sample_metrics:
            lines.append(f"OOS Win Rate: {self.out_of_sample_metrics.win_rate:.1%}")
            lines.append(f"OOS p-value: {self.out_of_sample_metrics.p_value_vs_random:.4f}")

        if self.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


class ExperimentRunner:
    """실험 실행기"""

    def __init__(self, data_source: Any = None,
                 hypotheses_path: str = None):
        """
        Args:
            data_source: 가격 데이터 소스 (DataFrame 또는 DB 연결)
            hypotheses_path: hypotheses.yaml 경로
        """
        self.data_source = data_source
        self.loader = HypothesisLoader(hypotheses_path)
        self.criteria = self.loader.get_validation_criteria()
        self.validator = WalkForwardValidator(self.criteria)
        self.metrics_calc = MetricsCalculator()
        self.evaluator = ConditionEvaluator()

        self._trade_generator: Optional[Callable] = None

    def set_trade_generator(self, generator: Callable[[str, str, Dict], List[TradeResult]]):
        """
        거래 생성 함수 설정

        Args:
            generator: (start_date, end_date, conditions) -> List[TradeResult]
        """
        self._trade_generator = generator

    def run(self, hypothesis_id: str,
            config: ExperimentConfig = None) -> ExperimentReport:
        """
        단일 가설 실험 실행

        Args:
            hypothesis_id: 가설 ID
            config: 실험 설정

        Returns:
            ExperimentReport
        """
        if config is None:
            config = ExperimentConfig(hypothesis_id=hypothesis_id)

        if self._trade_generator is None:
            raise ValueError("Trade generator not set. Call set_trade_generator first.")

        # 가설 로드
        hypothesis = self.loader.get_hypothesis(hypothesis_id)
        if hypothesis is None:
            raise ValueError(f"Hypothesis not found: {hypothesis_id}")

        if config.verbose:
            print(f"\n{'='*60}")
            print(f"Running: {hypothesis.name}")
            print(f"Type: {hypothesis.type.value}")
            print(f"{'='*60}\n")

        # Walk-Forward 검증
        wf_result = None
        is_metrics = None
        oos_metrics = None

        if config.run_walk_forward:
            wf_result = self.validator.validate(
                hypothesis,
                self._trade_generator,
                n_windows=config.n_windows
            )

            # 첫 번째 윈도우의 IS/OOS 메트릭스
            if wf_result.windows:
                is_metrics = wf_result.windows[0].train_metrics
                oos_metrics = wf_result.windows[0].test_metrics

            if config.verbose:
                self._print_wf_result(wf_result)

        # 전체 기간 거래 (통계용)
        all_trades = self._trade_generator(
            hypothesis.backtest.start_date,
            hypothesis.backtest.end_date,
            hypothesis.conditions
        )

        # 리포트 생성
        report = ExperimentReport(
            hypothesis_id=hypothesis_id,
            hypothesis_name=hypothesis.name,
            run_at=datetime.now().isoformat(),
            config=config,
            total_trades=len(all_trades),
            in_sample_metrics=is_metrics,
            out_of_sample_metrics=oos_metrics,
            walk_forward_result=wf_result,
            verdict=wf_result.verdict if wf_result else "NOT_VALIDATED",
            recommendations=wf_result.recommendations if wf_result else []
        )

        # 결과 저장
        if config.save_results:
            self._save_report(report, config.output_dir)

        return report

    def run_all_actionable(self, config: ExperimentConfig = None) -> Dict[str, ExperimentReport]:
        """실행 가능한 모든 가설 테스트"""
        results = {}
        actionable = self.loader.get_actionable()

        for hypothesis in actionable:
            cfg = config or ExperimentConfig(hypothesis_id=hypothesis.id)
            cfg.hypothesis_id = hypothesis.id

            try:
                report = self.run(hypothesis.id, cfg)
                results[hypothesis.id] = report
            except Exception as e:
                print(f"Error running {hypothesis.id}: {e}")

        return results

    def run_parameter_sweep(self, hypothesis_id: str) -> Dict[str, ExperimentReport]:
        """파라미터 스윕 실행"""
        hypothesis = self.loader.get_hypothesis(hypothesis_id)
        if hypothesis is None:
            raise ValueError(f"Hypothesis not found: {hypothesis_id}")

        combinations = hypothesis.get_sweep_combinations()
        results = {}

        for i, params in enumerate(combinations):
            print(f"\nSweep {i+1}/{len(combinations)}: {params}")

            # 파라미터 적용된 조건 생성
            modified_conditions = self._apply_parameters(hypothesis.conditions, params)

            # 임시 가설 생성
            temp_hypothesis = Hypothesis(
                id=f"{hypothesis_id}_sweep_{i}",
                name=f"{hypothesis.name} (Sweep {i})",
                description=f"Parameter sweep: {params}",
                status=hypothesis.status,
                type=hypothesis.type,
                created_at=datetime.now().strftime('%Y-%m-%d'),
                conditions=modified_conditions,
                backtest=hypothesis.backtest,
                parameters={}
            )

            # 검증
            wf_result = self.validator.validate(
                temp_hypothesis,
                self._trade_generator
            )

            config = ExperimentConfig(
                hypothesis_id=temp_hypothesis.id,
                save_results=False
            )

            report = ExperimentReport(
                hypothesis_id=temp_hypothesis.id,
                hypothesis_name=temp_hypothesis.name,
                run_at=datetime.now().isoformat(),
                config=config,
                total_trades=sum(w.test_metrics.total_trades for w in wf_result.windows),
                in_sample_metrics=wf_result.windows[0].train_metrics if wf_result.windows else None,
                out_of_sample_metrics=wf_result.windows[0].test_metrics if wf_result.windows else None,
                walk_forward_result=wf_result,
                verdict=wf_result.verdict,
                recommendations=wf_result.recommendations
            )

            results[str(params)] = report

        # 베스트 파라미터 찾기
        best_params = max(results.items(),
                          key=lambda x: x[1].out_of_sample_metrics.win_rate
                          if x[1].out_of_sample_metrics else 0)
        print(f"\nBest parameters: {best_params[0]}")

        return results

    def _apply_parameters(self, conditions: Dict, params: Dict) -> Dict:
        """조건에 파라미터 적용"""
        import copy
        modified = copy.deepcopy(conditions)

        def replace_param(obj, params):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in params:
                        obj[key] = {'operator': obj[key].get('operator', '=='),
                                    'value': params[key]}
                    else:
                        replace_param(value, params)
            elif isinstance(obj, list):
                for item in obj:
                    replace_param(item, params)

        replace_param(modified, params)
        return modified

    def _print_wf_result(self, result: WalkForwardResult):
        """Walk-Forward 결과 출력"""
        print(f"Walk-Forward Validation Results:")
        print(f"  Windows: {len(result.windows)}")
        print(f"  Pass Rate: {result.pass_rate:.0%}")
        print(f"  Train Win Rate: {result.avg_train_win_rate:.1%}")
        print(f"  Test Win Rate: {result.avg_test_win_rate:.1%}")
        print(f"  Decay: {result.win_rate_decay:+.1%}")
        print(f"  vs Random: {result.test_vs_random:+.1%}")
        print(f"  Verdict: {result.verdict}")

        if result.recommendations:
            print("\n  Recommendations:")
            for rec in result.recommendations:
                print(f"    - {rec}")

    def _save_report(self, report: ExperimentReport, output_dir: str):
        """리포트 저장"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report.hypothesis_id}_{timestamp}.json"

        with open(output_path / filename, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        print(f"\nReport saved: {output_path / filename}")


class QuickExperiment:
    """빠른 실험용 헬퍼"""

    def __init__(self, data_source: Any = None):
        self.data_source = data_source
        self.metrics_calc = MetricsCalculator()

    def test_filter(self, filter_fn: Callable[[Dict], bool],
                    trades: List[TradeResult],
                    description: str = "") -> Dict:
        """
        필터 함수 빠른 테스트

        Args:
            filter_fn: 거래 허용 여부 함수 (state -> bool)
            trades: 전체 거래
            description: 설명

        Returns:
            비교 결과
        """
        # 필터 적용
        filtered_trades = [t for t in trades
                          if filter_fn({'state': t.state_at_entry})]

        # 지표 계산
        all_metrics = self.metrics_calc.calculate(trades, "all")
        filtered_metrics = self.metrics_calc.calculate(filtered_trades, "filtered")

        improvement = filtered_metrics.win_rate - all_metrics.win_rate

        return {
            'description': description,
            'original': {
                'trades': all_metrics.total_trades,
                'win_rate': f"{all_metrics.win_rate:.1%}",
                'return': f"{all_metrics.total_return:.1%}"
            },
            'filtered': {
                'trades': filtered_metrics.total_trades,
                'win_rate': f"{filtered_metrics.win_rate:.1%}",
                'return': f"{filtered_metrics.total_return:.1%}"
            },
            'improvement': f"{improvement:+.1%}",
            'trades_removed': all_metrics.total_trades - filtered_metrics.total_trades
        }

    def compare_strategies(self, strategies: Dict[str, Callable],
                          trades: List[TradeResult]) -> Dict:
        """여러 전략 비교"""
        results = {}

        for name, filter_fn in strategies.items():
            results[name] = self.test_filter(filter_fn, trades, name)

        # 랭킹
        ranked = sorted(results.items(),
                       key=lambda x: float(x[1]['filtered']['win_rate'].rstrip('%')),
                       reverse=True)

        return {
            'strategies': results,
            'ranking': [name for name, _ in ranked],
            'best': ranked[0][0] if ranked else None
        }


# 편의 함수
def run_experiment(hypothesis_id: str,
                  trade_generator: Callable,
                  hypotheses_path: str = None) -> ExperimentReport:
    """실험 실행 헬퍼"""
    runner = ExperimentRunner(hypotheses_path=hypotheses_path)
    runner.set_trade_generator(trade_generator)
    return runner.run(hypothesis_id)


def list_hypotheses(hypotheses_path: str = None) -> List[Dict]:
    """가설 목록 조회"""
    loader = HypothesisLoader(hypotheses_path)
    hypotheses = loader.load()
    return [h.to_dict() for h in hypotheses.values()]
