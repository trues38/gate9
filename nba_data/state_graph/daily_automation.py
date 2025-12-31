#!/usr/bin/env python3
"""
일일 자동화 파이프라인 (Daily Automation Pipeline)

매일 실행되는 정량 데이터 수집:
1. 어제의 모든 경기 결과 수집 (BoxScores)
2. PlayerRecentForm 업데이트 (각 선수의 3시즌 최근 성적)
3. RefereeStats 업데이트 (심판의 최근 통계)
4. TeamStrength 재계산 (팀 강도)
5. CoachStats 업데이트 (감독 통계)

자동화 실행 시간: 매일 UTC 09:00 (KST 18:00)
"""

import subprocess
import sys
import os
from datetime import datetime, timedelta
import json


class DailyAutomationPipeline:
    """일일 자동화 파이프라인 관리"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.base_dir, '.automation_logs')
        os.makedirs(self.log_dir, exist_ok=True)
        self.today = datetime.now().strftime('%Y-%m-%d')

    def log(self, message, level='INFO'):
        """로그 기록"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        # 파일에도 기록
        log_file = os.path.join(self.log_dir, f'automation_{self.today}.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')

    def run_script(self, script_name, description):
        """Python 스크립트 실행"""
        script_path = os.path.join(self.base_dir, script_name)

        if not os.path.exists(script_path):
            self.log(f"스크립트 없음: {script_name}", 'ERROR')
            return False

        self.log(f"시작: {description}")

        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=600  # 10분 타임아웃
            )

            if result.returncode == 0:
                self.log(f"완료: {description}")
                return True
            else:
                self.log(f"실패: {description} - {result.stderr}", 'ERROR')
                return False

        except subprocess.TimeoutExpired:
            self.log(f"타임아웃: {description}", 'ERROR')
            return False
        except Exception as e:
            self.log(f"오류: {description} - {str(e)}", 'ERROR')
            return False

    def run_daily_pipeline(self):
        """일일 자동화 파이프라인 실행"""

        self.log("="*70)
        self.log(f"일일 자동화 파이프라인 시작 - {self.today}")
        self.log("="*70)

        results = {}

        # 1. 어제의 경기 결과 수집
        results['boxscores'] = self.run_script(
            'crawl_current_season_boxscores.py',
            '어제 경기 결과 수집'
        )

        # 2. 선수-팀 관계 생성
        results['player_team'] = self.run_script(
            'create_player_team_relations.py',
            '선수-팀 관계(PLAYS_FOR) 생성'
        )

        # 3. PlayerRecentForm 업데이트
        results['player_form'] = self.run_script(
            'generate_player_recent_form.py',
            'PlayerRecentForm 노드 업데이트'
        )

        # 4. RefereeStats 업데이트
        results['referee_stats'] = self.run_script(
            'generate_referee_stats.py',
            'RefereeStats 노드 업데이트'
        )

        # 5. TeamStrength 재계산
        results['team_strength'] = self.run_script(
            'calculate_team_strength.py',
            'TeamStrength 재계산'
        )

        # 6. CoachStats 업데이트
        results['coach_stats'] = self.run_script(
            'calculate_coach_stats.py',
            'CoachStats 노드 업데이트'
        )

        # 결과 정리
        self.log("="*70)
        self.log("일일 자동화 파이프라인 결과")
        self.log("="*70)

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        for task, status in results.items():
            status_str = "✅" if status else "❌"
            self.log(f"{status_str} {task}")

        self.log(f"총 {success_count}/{total_count} 완료")

        # 결과를 JSON으로 저장
        result_file = os.path.join(self.log_dir, f'result_{self.today}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': self.today,
                'timestamp': datetime.now().isoformat(),
                'results': results,
                'success_count': success_count,
                'total_count': total_count
            }, f, ensure_ascii=False, indent=2)

        self.log("="*70)
        self.log("✅ 일일 자동화 파이프라인 완료")
        self.log("="*70)

        return success_count == total_count


def main():
    pipeline = DailyAutomationPipeline()
    success = pipeline.run_daily_pipeline()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
