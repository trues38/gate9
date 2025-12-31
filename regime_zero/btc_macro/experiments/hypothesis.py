"""
Hypothesis - 가설 정의 및 파서

가설 기반 실험을 위한 데이터 구조:
- Hypothesis: 단일 가설 정의
- HypothesisLoader: YAML 파서
- ConditionEvaluator: 조건 평가
"""

import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
from pathlib import Path


class HypothesisStatus(Enum):
    """가설 상태"""
    DRAFT = "draft"
    TESTING = "testing"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class HypothesisType(Enum):
    """가설 유형"""
    FILTER = "filter"           # 진입 필터
    ENTRY = "entry"             # 진입 시그널
    EXIT = "exit"               # 청산 시그널
    POSITION_SIZE = "position_size"  # 포지션 사이징


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    start_date: str
    end_date: str
    train_end: str              # IS 기간 끝
    initial_capital: float = 10000
    position_size: float = 0.1


@dataclass
class ExperimentResult:
    """실험 결과"""
    period: str
    trades: int
    win_rate: float
    total_return: float
    max_drawdown: float
    sharpe: float
    p_value: Optional[float] = None
    vs_random: Optional[str] = None


@dataclass
class ValidationCriteria:
    """검증 기준"""
    win_rate_edge: float = 0.08
    p_value_threshold: float = 0.1
    max_drawdown_limit: float = 0.25
    min_samples: int = 20
    oos_ratio: float = 0.4


@dataclass
class Parameter:
    """스윕 가능 파라미터"""
    name: str
    default: Any
    sweep: List[Any] = field(default_factory=list)


@dataclass
class Hypothesis:
    """단일 가설 정의"""
    id: str
    name: str
    description: str
    status: HypothesisStatus
    type: HypothesisType
    created_at: str

    # 조건들
    conditions: Dict[str, Any]

    # 백테스트 설정
    backtest: BacktestConfig

    # 파라미터 (스윕 테스트용)
    parameters: Dict[str, Parameter] = field(default_factory=dict)

    # 결과 (테스트 후)
    in_sample_results: Optional[ExperimentResult] = None
    out_of_sample_results: Optional[ExperimentResult] = None

    # 판정
    verdict: Optional[str] = None
    rejection_reason: Optional[str] = None
    validated_at: Optional[str] = None

    # 주요 검증 지표 (기본: win_rate)
    primary_metric: str = "win_rate"

    def is_actionable(self) -> bool:
        """실행 가능한 가설인지"""
        return self.status in [HypothesisStatus.DRAFT, HypothesisStatus.TESTING]

    def is_validated(self) -> bool:
        """검증 통과했는지"""
        return self.status == HypothesisStatus.VALIDATED

    def get_sweep_combinations(self) -> List[Dict[str, Any]]:
        """파라미터 스윕 조합 생성"""
        if not self.parameters:
            return [{}]

        from itertools import product

        param_names = list(self.parameters.keys())
        param_values = [
            p.sweep if p.sweep else [p.default]
            for p in self.parameters.values()
        ]

        combinations = []
        for combo in product(*param_values):
            combinations.append(dict(zip(param_names, combo)))

        return combinations

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "type": self.type.value,
            "conditions": self.conditions,
            "verdict": self.verdict
        }


class HypothesisLoader:
    """YAML에서 가설 로드"""

    def __init__(self, yaml_path: str = None):
        if yaml_path is None:
            yaml_path = Path(__file__).parent / "hypotheses.yaml"
        self.yaml_path = Path(yaml_path)
        self._hypotheses: Dict[str, Hypothesis] = {}
        self._validation_criteria: Optional[ValidationCriteria] = None

    def load(self) -> Dict[str, Hypothesis]:
        """YAML 파일 로드"""
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 검증 기준 로드
        vc = data.get('validation_criteria', {})
        self._validation_criteria = ValidationCriteria(
            win_rate_edge=vc.get('win_rate_edge', 0.08),
            p_value_threshold=vc.get('p_value_threshold', 0.1),
            max_drawdown_limit=vc.get('max_drawdown_limit', 0.25),
            min_samples=vc.get('min_samples', 20),
            oos_ratio=vc.get('oos_ratio', 0.4)
        )

        # 가설들 로드
        for h_data in data.get('hypotheses', []):
            hypothesis = self._parse_hypothesis(h_data)
            self._hypotheses[hypothesis.id] = hypothesis

        return self._hypotheses

    def _parse_hypothesis(self, data: dict) -> Hypothesis:
        """단일 가설 파싱"""
        # 백테스트 설정
        bt_data = data.get('backtest', {})
        backtest = BacktestConfig(
            start_date=bt_data.get('start_date', '2020-01-01'),
            end_date=bt_data.get('end_date', '2025-12-26'),
            train_end=bt_data.get('train_end', '2022-12-31'),
            initial_capital=bt_data.get('initial_capital', 10000),
            position_size=bt_data.get('position_size', 0.1)
        )

        # 파라미터
        parameters = {}
        for param_name, param_data in data.get('parameters', {}).items():
            parameters[param_name] = Parameter(
                name=param_name,
                default=param_data.get('default'),
                sweep=param_data.get('sweep', [])
            )

        # 결과 (있으면)
        results_data = data.get('results') or {}
        in_sample = None
        out_of_sample = None

        if 'in_sample' in results_data:
            is_data = results_data['in_sample']
            in_sample = ExperimentResult(
                period=is_data.get('period', ''),
                trades=is_data.get('trades', 0),
                win_rate=is_data.get('win_rate', 0),
                total_return=is_data.get('total_return', 0),
                max_drawdown=is_data.get('max_drawdown', 0),
                sharpe=is_data.get('sharpe', 0)
            )

        if 'out_of_sample' in results_data:
            oos_data = results_data['out_of_sample']
            out_of_sample = ExperimentResult(
                period=oos_data.get('period', ''),
                trades=oos_data.get('trades', 0),
                win_rate=oos_data.get('win_rate', 0),
                total_return=oos_data.get('total_return', 0),
                max_drawdown=oos_data.get('max_drawdown', 0),
                sharpe=oos_data.get('sharpe', 0),
                p_value=oos_data.get('p_value'),
                vs_random=oos_data.get('vs_random')
            )

        return Hypothesis(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            status=HypothesisStatus(data.get('status', 'draft')),
            type=HypothesisType(data.get('type', 'filter')),
            created_at=data.get('created_at', datetime.now().strftime('%Y-%m-%d')),
            conditions=data.get('conditions', {}),
            backtest=backtest,
            parameters=parameters,
            in_sample_results=in_sample,
            out_of_sample_results=out_of_sample,
            verdict=data.get('verdict'),
            rejection_reason=data.get('rejection_reason'),
            validated_at=data.get('validated_at'),
            primary_metric=data.get('primary_metric', 'win_rate')
        )

    def get_validation_criteria(self) -> ValidationCriteria:
        """검증 기준 반환"""
        if self._validation_criteria is None:
            self.load()
        return self._validation_criteria

    def get_hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """특정 가설 반환"""
        if not self._hypotheses:
            self.load()
        return self._hypotheses.get(hypothesis_id)

    def get_actionable(self) -> List[Hypothesis]:
        """실행 가능한 가설들"""
        if not self._hypotheses:
            self.load()
        return [h for h in self._hypotheses.values() if h.is_actionable()]

    def get_validated(self) -> List[Hypothesis]:
        """검증 통과한 가설들"""
        if not self._hypotheses:
            self.load()
        return [h for h in self._hypotheses.values() if h.is_validated()]

    def get_by_status(self, status: HypothesisStatus) -> List[Hypothesis]:
        """상태별 가설들"""
        if not self._hypotheses:
            self.load()
        return [h for h in self._hypotheses.values() if h.status == status]


class ConditionEvaluator:
    """조건 평가기"""

    def __init__(self):
        self._operators = {
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            'in': lambda a, b: a in b,
            'contains': lambda a, b: b in a,
        }

    def evaluate(self, conditions: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """
        조건 평가

        Args:
            conditions: 조건 딕셔너리
            state: 현재 상태 딕셔너리

        Returns:
            조건 충족 여부
        """
        for cond_group in conditions:
            if isinstance(cond_group, dict):
                if not self._evaluate_condition(cond_group, state):
                    return False
            elif isinstance(cond_group, list):
                # OR 조건
                if not any(self._evaluate_condition(c, state) for c in cond_group):
                    return False
        return True

    def _evaluate_condition(self, condition: dict, state: dict) -> bool:
        """단일 조건 평가"""
        for key, value in condition.items():
            if key == 'or':
                # OR 조건
                return any(self._evaluate_condition(c, state) for c in value)

            state_value = state.get(key)
            if state_value is None:
                return False

            if isinstance(value, dict):
                # 연산자 조건: {operator: ">=", value: 30}
                op = value.get('operator', '==')
                target = value.get('value')
                if not self._operators[op](state_value, target):
                    return False
            elif isinstance(value, list):
                # 리스트 조건: ["weak", "neutral"]
                if state_value not in value:
                    # 부분 매칭도 체크
                    if not any(v in str(state_value) for v in value):
                        return False
            else:
                # 단순 비교
                if state_value != value:
                    return False

        return True

    def check_avoid(self, conditions: List[Dict], state: Dict) -> bool:
        """회피 조건 체크 (하나라도 해당하면 True)"""
        for cond in conditions:
            if self._evaluate_condition(cond, state):
                return True
        return False

    def check_entry(self, conditions: List[Dict], state: Dict) -> bool:
        """진입 조건 체크 (모두 충족해야 True)"""
        return all(self._evaluate_condition(c, state) for c in conditions)


# 편의 함수
def load_hypotheses(yaml_path: str = None) -> Dict[str, Hypothesis]:
    """가설 로드 헬퍼"""
    loader = HypothesisLoader(yaml_path)
    return loader.load()


def get_validated_hypotheses(yaml_path: str = None) -> List[Hypothesis]:
    """검증된 가설만 로드"""
    loader = HypothesisLoader(yaml_path)
    loader.load()
    return loader.get_validated()
