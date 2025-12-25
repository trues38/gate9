#!/usr/bin/env python3
"""
2시즌 vs 3시즌 데이터 효과 정량 분석
시뮬레이션으로 샘플 사이즈 증가 효과 측정
"""

import math
from typing import Dict

class DataEfficiencyAnalyzer:
    """데이터 양에 따른 효율성 분석"""

    def __init__(self):
        self.teams = 30
        # 각 팀이 홈/원정에서 가능한 휴식일 조합
        self.rest_day_combinations = [0, 1, 2, 3, 4, 5, 6, 7]
        self.locations = 2  # home, away

    def calculate_expected_samples(self, total_games: int) -> Dict:
        """총 경기 수에서 각 조합별 예상 샘플 수"""

        # 각 팀은 시즌당 82경기 (41 홈 + 41 원정)
        games_per_team = total_games / self.teams
        games_per_location = games_per_team / 2  # 홈/원정 각각

        # 휴식일 분포 (경험적 추정)
        # 0일(백투백): 15%, 1일: 40%, 2일: 25%, 3일: 12%, 4+일: 8%
        rest_distribution = {
            0: 0.15,
            1: 0.40,
            2: 0.25,
            3: 0.12,
            4: 0.05,
            5: 0.02,
            6: 0.01,
            7: 0.00
        }

        results = {
            'total_combinations': self.teams * len(self.rest_day_combinations) * self.locations,
            'samples_by_rest': {},
            'confidence_levels': {
                'excellent': 0,  # 30+ games
                'good': 0,       # 20-29 games
                'acceptable': 0, # 10-19 games
                'poor': 0,       # 5-9 games
                'very_poor': 0   # <5 games
            }
        }

        for rest_days, probability in rest_distribution.items():
            expected_samples = games_per_location * probability
            results['samples_by_rest'][rest_days] = expected_samples

            # 이 휴식일을 사용하는 팀×장소 조합 = 30팀 × 2위치 = 60개
            combinations_with_this_rest = self.teams * self.locations

            # 각 조합의 샘플 분류
            if expected_samples >= 30:
                results['confidence_levels']['excellent'] += combinations_with_this_rest
            elif expected_samples >= 20:
                results['confidence_levels']['good'] += combinations_with_this_rest
            elif expected_samples >= 10:
                results['confidence_levels']['acceptable'] += combinations_with_this_rest
            elif expected_samples >= 5:
                results['confidence_levels']['poor'] += combinations_with_this_rest
            else:
                results['confidence_levels']['very_poor'] += combinations_with_this_rest

        return results

    def calculate_prediction_variance(self, sample_size: int, win_rate: float = 0.5) -> float:
        """예측 분산 계산 (작을수록 좋음)"""
        if sample_size < 1:
            return float('inf')

        # 이항 분포의 표준편차
        variance = (win_rate * (1 - win_rate)) / sample_size
        std_dev = math.sqrt(variance)

        # 95% 신뢰구간 (±1.96 * std_dev)
        confidence_interval = 1.96 * std_dev
        return confidence_interval

    def calculate_staleness_penalty(self, seasons: int) -> float:
        """데이터 오래됨에 따른 페널티 (0-1, 1이 최악)"""
        # 1시즌: 0% 페널티
        # 2시즌: 5% 페널티 (1년 전 데이터 일부 관련성 하락)
        # 3시즌: 15% 페널티 (2년 전 데이터 많이 오래됨)
        # 4시즌: 30% 페널티 (3년 전 데이터 대부분 무관)

        penalty_map = {
            1: 0.00,
            2: 0.05,
            3: 0.15,
            4: 0.30,
            5: 0.50
        }

        return penalty_map.get(seasons, 0.50)

    def calculate_overall_efficiency(self, total_games: int, seasons: int) -> Dict:
        """전체 효율성 계산"""
        samples = self.calculate_expected_samples(total_games)

        # 평균 샘플 사이즈 (1일 휴식 기준 - 가장 흔함)
        avg_sample_size = samples['samples_by_rest'][1]

        # 예측 정확도 (분산의 역수 - 클수록 좋음)
        prediction_variance = self.calculate_prediction_variance(avg_sample_size)
        prediction_accuracy = 1 / (1 + prediction_variance)  # 0-1 사이 값

        # 데이터 신선도 (1 - 페널티)
        staleness_penalty = self.calculate_staleness_penalty(seasons)
        data_freshness = 1 - staleness_penalty

        # 종합 효율성 = 정확도 × 신선도
        # 가중치: 정확도 60%, 신선도 40%
        overall_efficiency = (prediction_accuracy * 0.6) + (data_freshness * 0.4)

        # 신뢰 가능한 조합 비율
        total_combos = samples['confidence_levels']['excellent'] + \
                      samples['confidence_levels']['good'] + \
                      samples['confidence_levels']['acceptable']

        all_combos = sum(samples['confidence_levels'].values())
        reliable_ratio = total_combos / all_combos if all_combos > 0 else 0

        return {
            'total_games': total_games,
            'seasons': seasons,
            'avg_sample_size': round(avg_sample_size, 1),
            'prediction_variance': round(prediction_variance, 3),
            'prediction_accuracy': round(prediction_accuracy, 3),
            'data_freshness': round(data_freshness, 3),
            'overall_efficiency': round(overall_efficiency, 3),
            'reliable_ratio': round(reliable_ratio, 3),
            'confidence_levels': samples['confidence_levels'],
            'samples_by_rest': samples['samples_by_rest']
        }

def main():
    analyzer = DataEfficiencyAnalyzer()

    print("=" * 90)
    print("2시즌 vs 3시즌 데이터 효과 정량 분석")
    print("=" * 90)

    scenarios = [
        {'name': '현재 (1시즌)', 'games': 927, 'seasons': 1},
        {'name': '2시즌 추가', 'games': 2157, 'seasons': 2},
        {'name': '3시즌 추가', 'games': 3387, 'seasons': 3},
    ]

    results = []
    for scenario in scenarios:
        result = analyzer.calculate_overall_efficiency(
            scenario['games'],
            scenario['seasons']
        )
        result['name'] = scenario['name']
        results.append(result)

    # 결과 출력
    print("\n" + "=" * 90)
    print("📊 시나리오별 상세 분석")
    print("=" * 90)

    for result in results:
        print(f"\n{'▶' * 3} {result['name']} (총 {result['total_games']:,}경기)")
        print("-" * 90)

        print(f"\n  📈 샘플 사이즈:")
        print(f"     평균 샘플 (1일 휴식): {result['avg_sample_size']}경기")

        print(f"\n  🎯 예측 품질:")
        print(f"     예측 분산: ±{result['prediction_variance']*100:.1f}%")
        print(f"     예측 정확도 점수: {result['prediction_accuracy']:.3f}")

        print(f"\n  ⏰ 데이터 신선도:")
        print(f"     신선도 점수: {result['data_freshness']:.3f}")
        print(f"     관련성 페널티: {(1-result['data_freshness'])*100:.0f}%")

        print(f"\n  ⚡ 종합 효율성:")
        print(f"     효율성 점수: {result['overall_efficiency']:.3f}")
        print(f"     신뢰 가능 조합 비율: {result['reliable_ratio']*100:.1f}%")

        print(f"\n  📋 신뢰도 분포:")
        total = sum(result['confidence_levels'].values())
        for level, count in result['confidence_levels'].items():
            pct = count / total * 100 if total > 0 else 0
            print(f"     {level:12s}: {count:3d}개 ({pct:5.1f}%)")

    # 비교 분석
    print("\n" + "=" * 90)
    print("🔍 2시즌 vs 3시즌 직접 비교")
    print("=" * 90)

    scenario_2 = results[1]
    scenario_3 = results[2]

    improvements = {
        '샘플 사이즈 증가': f"{scenario_2['avg_sample_size']:.1f} → {scenario_3['avg_sample_size']:.1f} ({(scenario_3['avg_sample_size']/scenario_2['avg_sample_size']-1)*100:+.1f}%)",
        '예측 정확도': f"{scenario_2['prediction_accuracy']:.3f} → {scenario_3['prediction_accuracy']:.3f} ({(scenario_3['prediction_accuracy']/scenario_2['prediction_accuracy']-1)*100:+.1f}%)",
        '데이터 신선도': f"{scenario_2['data_freshness']:.3f} → {scenario_3['data_freshness']:.3f} ({(scenario_3['data_freshness']/scenario_2['data_freshness']-1)*100:+.1f}%)",
        '종합 효율성': f"{scenario_2['overall_efficiency']:.3f} → {scenario_3['overall_efficiency']:.3f} ({(scenario_3['overall_efficiency']/scenario_2['overall_efficiency']-1)*100:+.1f}%)",
    }

    for metric, comparison in improvements.items():
        print(f"\n  {metric}:")
        print(f"    {comparison}")

    # 최종 판단
    print("\n" + "=" * 90)
    print("🎯 최종 판단")
    print("=" * 90)

    efficiency_diff = scenario_3['overall_efficiency'] - scenario_2['overall_efficiency']

    print(f"\n  2시즌 효율성: {scenario_2['overall_efficiency']:.3f}")
    print(f"  3시즌 효율성: {scenario_3['overall_efficiency']:.3f}")
    print(f"  차이: {efficiency_diff:+.3f} ({efficiency_diff/scenario_2['overall_efficiency']*100:+.1f}%)")

    if efficiency_diff > 0.02:  # 2% 이상 개선
        print(f"\n  ✅ 결론: 3시즌 추천!")
        print(f"     효율성이 {abs(efficiency_diff/scenario_2['overall_efficiency']*100):.1f}% 향상됨")
    elif efficiency_diff > -0.02:  # -2% ~ +2%
        print(f"\n  ⚠️  결론: 2시즌과 3시즌 비슷함")
        print(f"     샘플 증가 효과 vs 신선도 하락이 상쇄")
        print(f"     크롤링 비용 고려하여 결정")
    else:  # -2% 이하
        print(f"\n  ❌ 결론: 2시즌 추천!")
        print(f"     3시즌은 오히려 효율성 {abs(efficiency_diff/scenario_2['overall_efficiency']*100):.1f}% 감소")

    print(f"\n  💡 추가 고려사항:")
    print(f"     • 크롤링 시간: 2시즌 ~1시간, 3시즌 ~2시간")
    print(f"     • Neo4j 용량: 2시즌 ~100MB, 3시즌 ~150MB")
    print(f"     • 쿼리 속도: 2시즌 ~50ms, 3시즌 ~70ms")

    print("\n" + "=" * 90)

if __name__ == "__main__":
    main()
