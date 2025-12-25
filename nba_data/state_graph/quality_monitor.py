"""
전술 태깅 품질 관리 시스템
===========================
실시간 일관성 모니터링 + 자동 경고

Made with ❤️ by State Graph Engine
"""

from typing import Dict, List
from collections import defaultdict
import json


class QualityMonitor:
    """전술 태깅 품질 모니터"""

    def __init__(self):
        self.alerts = []

    def check_consistency(self, tactic_tags: List[Dict]) -> Dict:
        """
        전술 태깅 일관성 체크

        체크 항목:
        1. 같은 통계인데 다른 전술 태깅 (일관성 위배)
        2. confidence가 비정상적으로 높음 (과적합)
        3. sample_size가 작은데 confidence가 높음 (과신)
        4. 상호 모순되는 전술 (Gap Defense + Pace & Space 동시)
        """

        results = {
            'total_tags': len(tactic_tags),
            'inconsistencies': [],
            'warnings': [],
            'suspicious_tags': [],
            'quality_score': 1.0
        }

        # 1. 통계 유사도 체크
        inconsistencies = self._check_statistical_consistency(tactic_tags)
        results['inconsistencies'] = inconsistencies
        results['quality_score'] -= len(inconsistencies) * 0.1

        # 2. Confidence 과신 체크
        warnings = self._check_confidence_warnings(tactic_tags)
        results['warnings'] = warnings
        results['quality_score'] -= len(warnings) * 0.05

        # 3. 모순 전술 체크
        contradictions = self._check_contradictions(tactic_tags)
        results['suspicious_tags'] = contradictions
        results['quality_score'] -= len(contradictions) * 0.15

        results['quality_score'] = max(0.0, round(results['quality_score'], 2))

        return results

    def _check_statistical_consistency(self, tags: List[Dict]) -> List[Dict]:
        """같은 통계인데 다른 전술로 태깅된 경우 찾기"""

        inconsistencies = []

        # 통계 패턴으로 그룹화
        stat_groups = defaultdict(list)

        for tag in tags:
            # 통계 시그니처 생성 (반올림해서 유사도 판정)
            stats = tag.get('team_stats', {})
            signature = self._create_stat_signature(stats)

            stat_groups[signature].append(tag)

        # 같은 시그니처인데 다른 전술
        for signature, group in stat_groups.items():
            if len(group) < 2:
                continue

            tactics = set(tag['tactic_name'] for tag in group)
            if len(tactics) > 1:
                inconsistencies.append({
                    'signature': signature,
                    'games': [tag['game_id'] for tag in group],
                    'different_tactics': list(tactics),
                    'severity': 'high',
                    'explanation': f"동일한 통계 패턴인데 {len(tactics)}개 다른 전술로 태깅됨"
                })

        return inconsistencies

    def _create_stat_signature(self, stats: Dict) -> str:
        """통계 시그니처 생성 (유사도 판정용)"""

        # 주요 지표만 반올림
        keys = ['opponent_paint_points', 'three_point_rate', 'pace', 'offensive_rating']
        signature_parts = []

        for key in keys:
            value = stats.get(key, 0)
            # 반올림 (오차 5%)
            if 'rate' in key or 'pct' in key:
                rounded = round(value, 1)  # 0.1 단위
            else:
                rounded = round(value / 5) * 5  # 5 단위

            signature_parts.append(f"{key}:{rounded}")

        return "|".join(signature_parts)

    def _check_confidence_warnings(self, tags: List[Dict]) -> List[Dict]:
        """Confidence 과신 경고"""

        warnings = []

        for tag in tags:
            sample_size = tag.get('sample_size', 0)
            confidence = tag.get('confidence', 0)

            # 샘플 10개 미만인데 confidence 0.8 이상
            if sample_size < 10 and confidence >= 0.8:
                warnings.append({
                    'game_id': tag['game_id'],
                    'tactic': tag['tactic_name'],
                    'sample_size': sample_size,
                    'confidence': confidence,
                    'severity': 'medium',
                    'explanation': f"샘플 {sample_size}개인데 confidence {confidence}는 과신"
                })

            # 샘플 5개 미만인데 confidence 0.7 이상
            if sample_size < 5 and confidence >= 0.7:
                warnings.append({
                    'game_id': tag['game_id'],
                    'tactic': tag['tactic_name'],
                    'sample_size': sample_size,
                    'confidence': confidence,
                    'severity': 'high',
                    'explanation': f"샘플 {sample_size}개로는 신뢰 불가"
                })

        return warnings

    def _check_contradictions(self, tags: List[Dict]) -> List[Dict]:
        """모순되는 전술 태깅 체크"""

        contradictions = []

        # 같은 경기에 모순 전술이 태깅된 경우
        game_tactics = defaultdict(list)

        for tag in tags:
            game_tactics[tag['game_id']].append(tag['tactic_name'])

        # 모순 전술 쌍 정의
        contradictory_pairs = [
            ("Gap Defense", "Pace & Space"),  # 느린 템포 vs 빠른 템포
            ("Inside Spacing", "3-Point Heavy"),  # 인사이드 vs 아웃사이드
            ("20-30min Rotation", "Star Heavy Minutes")  # 균등 분배 vs 스타 집중
        ]

        for game_id, tactics in game_tactics.items():
            for pair in contradictory_pairs:
                if pair[0] in tactics and pair[1] in tactics:
                    contradictions.append({
                        'game_id': game_id,
                        'contradictory_tactics': list(pair),
                        'severity': 'high',
                        'explanation': f"{pair[0]}와 {pair[1]}는 동시에 불가능"
                    })

        return contradictions


# ============================================================================
# 자동 리포트 생성
# ============================================================================

def generate_quality_report(tactic_tags: List[Dict]) -> str:
    """품질 리포트 생성"""

    monitor = QualityMonitor()
    results = monitor.check_consistency(tactic_tags)

    report = []
    report.append("=" * 70)
    report.append("전술 태깅 품질 리포트")
    report.append("=" * 70)
    report.append(f"\n총 태그 수: {results['total_tags']}")
    report.append(f"품질 점수: {results['quality_score']} / 1.0")

    # 일관성 문제
    if results['inconsistencies']:
        report.append(f"\n⚠️  일관성 문제 ({len(results['inconsistencies'])}개):")
        for inc in results['inconsistencies'][:5]:  # 상위 5개만
            report.append(f"  - {inc['explanation']}")
            report.append(f"    경기: {', '.join(inc['games'][:3])}...")
            report.append(f"    전술: {', '.join(inc['different_tactics'])}")

    # 경고
    if results['warnings']:
        report.append(f"\n⚠️  Confidence 경고 ({len(results['warnings'])}개):")
        for warn in results['warnings'][:5]:
            report.append(f"  - {warn['explanation']}")
            report.append(f"    경기: {warn['game_id']}, 전술: {warn['tactic']}")

    # 모순
    if results['suspicious_tags']:
        report.append(f"\n🚨 모순 전술 ({len(results['suspicious_tags'])}개):")
        for sus in results['suspicious_tags']:
            report.append(f"  - {sus['explanation']}")
            report.append(f"    경기: {sus['game_id']}")

    # 권장 사항
    report.append("\n" + "=" * 70)
    report.append("권장 조치:")
    report.append("=" * 70)

    if results['quality_score'] < 0.7:
        report.append("🚨 품질이 낮습니다. 전술 정의와 통계 시그니처를 재검토하세요.")
    elif results['quality_score'] < 0.85:
        report.append("⚠️  일부 개선이 필요합니다. 일관성 문제를 해결하세요.")
    else:
        report.append("✅ 품질이 양호합니다!")

    if results['inconsistencies']:
        report.append("\n1. 일관성 문제 해결:")
        report.append("   - TACTIC_SIGNATURES의 통계 조건을 더 엄격하게 조정")
        report.append("   - 비슷한 통계인데 다른 전술은 LLM 재검증 필요")

    if results['warnings']:
        report.append("\n2. Confidence 조정:")
        report.append("   - 샘플 10개 미만: Bayesian Prior 강화")
        report.append("   - 샘플 5개 미만: Transfer Learning 필수")

    if results['suspicious_tags']:
        report.append("\n3. 모순 전술 제거:")
        report.append("   - 같은 게임에 모순 전술 태깅 불가")
        report.append("   - 전술 카테고리 재분류 필요")

    return "\n".join(report)


# ============================================================================
# 실시간 모니터링
# ============================================================================

def monitor_new_tag(new_tag: Dict, existing_tags: List[Dict]) -> Dict:
    """
    새 태그 추가 시 실시간 검증

    Returns:
        {'approved': True/False, 'warnings': [...]}
    """

    monitor = QualityMonitor()

    # 기존 태그와 비교
    all_tags = existing_tags + [new_tag]
    results = monitor.check_consistency(all_tags)

    # 이 태그와 관련된 문제만 추출
    related_issues = []

    for inc in results['inconsistencies']:
        if new_tag['game_id'] in inc['games']:
            related_issues.append(inc)

    for warn in results['warnings']:
        if warn['game_id'] == new_tag['game_id']:
            related_issues.append(warn)

    for sus in results['suspicious_tags']:
        if sus['game_id'] == new_tag['game_id']:
            related_issues.append(sus)

    # 승인 여부 결정
    high_severity = sum(1 for issue in related_issues if issue.get('severity') == 'high')
    approved = high_severity == 0

    return {
        'approved': approved,
        'issues': related_issues,
        'recommendation': "승인" if approved else "재검토 필요"
    }


# ============================================================================
# 예시 실행
# ============================================================================

if __name__ == "__main__":
    # 예시 데이터
    tactic_tags = [
        {
            'game_id': '401810220',
            'team': 'OKC',
            'tactic_name': 'Gap Defense',
            'confidence': 0.85,
            'sample_size': 15,
            'team_stats': {
                'opponent_paint_points': 38,
                'three_point_rate': 0.28,
                'pace': 98,
                'offensive_rating': 118
            }
        },
        {
            'game_id': '401810221',
            'team': 'OKC',
            'tactic_name': 'Pace & Space',  # 모순!
            'confidence': 0.75,
            'sample_size': 12,
            'team_stats': {
                'opponent_paint_points': 40,
                'three_point_rate': 0.30,
                'pace': 95,
                'offensive_rating': 115
            }
        },
        {
            'game_id': '401810222',
            'team': 'MIA',
            'tactic_name': 'Gap Defense',  # 같은 통계인데 다른 팀
            'confidence': 0.90,  # 과신!
            'sample_size': 3,    # 샘플 부족!
            'team_stats': {
                'opponent_paint_points': 39,
                'three_point_rate': 0.28,
                'pace': 100,
                'offensive_rating': 116
            }
        }
    ]

    # 품질 리포트 생성
    report = generate_quality_report(tactic_tags)
    print(report)

    # 새 태그 실시간 검증
    print("\n" + "=" * 70)
    print("새 태그 실시간 검증")
    print("=" * 70)

    new_tag = {
        'game_id': '401810220',  # 같은 게임
        'team': 'OKC',
        'tactic_name': 'Pace & Space',  # Gap Defense와 모순!
        'confidence': 0.70,
        'sample_size': 10,
        'team_stats': {}
    }

    validation = monitor_new_tag(new_tag, tactic_tags)
    print(f"\n승인 여부: {validation['approved']}")
    print(f"권장: {validation['recommendation']}")
    if validation['issues']:
        print(f"\n발견된 문제 ({len(validation['issues'])}개):")
        for issue in validation['issues']:
            print(f"  - {issue.get('explanation', 'Unknown issue')}")
