"""
Experiment Layer - 가설 기반 전략 테스트 프레임워크

Core 엔진과 분리된 실험 레이어:
- Hypothesis: 테스트 가설 정의
- Runner: 실험 실행
- WalkForward: OOS 검증
- Metrics: 표준 성과 지표
"""

from .hypothesis import Hypothesis, HypothesisLoader
from .runner import ExperimentRunner
from .walk_forward import WalkForwardValidator
from .metrics import ExperimentMetrics

__all__ = [
    'Hypothesis',
    'HypothesisLoader',
    'ExperimentRunner',
    'WalkForwardValidator',
    'ExperimentMetrics'
]
