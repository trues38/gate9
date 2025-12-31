#!/usr/bin/env python3
"""
G9 Data Validator - DVSS v2.0 (Data Validation Scoring System)
==============================================================
4-Layer Validation System

L1: Completeness (20%) - 필수 데이터 존재 여부
L2: Range (20%) - 물리적 가능 범위
L3: Rate of Change (35%) - 일간 변화율 검증 (핵심!)
L4: Cross-Validation (25%) - 이전 데이터와 일관성

Grade System:
- A (90+): Excellent - 자동 발행
- B (75-89): Good - 자동 발행
- C (60-74): Fair - 수동 검토 필요
- F (<60): Fail - 발행 차단
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import yfinance as yf


class DVSSGrade(Enum):
    A = "A"  # 90+ Excellent
    B = "B"  # 75-89 Good
    C = "C"  # 60-74 Fair (manual review)
    F = "F"  # <60 Fail (blocked)


class ValidationStatus(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class DVSSReport:
    """DVSS Validation Report"""
    score: int
    max_score: int
    grade: DVSSGrade
    can_publish: bool

    l1_score: int  # Completeness
    l2_score: int  # Range
    l3_score: int  # Rate of Change
    l4_score: int  # Cross-Validation

    l1_details: Dict
    l2_details: Dict
    l3_details: Dict
    l4_details: Dict

    issues: List[str]
    warnings: List[str]


class DataValidator:
    """
    DVSS v2.0 - Yahoo Finance 단일 소스
    Supabase/SQLite 의존성 제거
    """

    # Yahoo Finance 심볼 매핑
    SYMBOLS = {
        'VIX': '^VIX',
        'SPX': '^GSPC',
        'DXY': 'DX-Y.NYB',
        'TNX': '^TNX',      # 10Y Treasury
        'HYG': 'HYG',       # High Yield ETF
        'LQD': 'LQD',       # Investment Grade ETF
        'GOLD': 'GC=F',
    }

    # L2: Range 기준
    VALID_RANGES = {
        'VIX': (9, 80),
        'SPX': (3000, 10000),
        'DXY': (70, 130),
        'TNX': (0, 10),       # 0-10%
        'HYG': (50, 120),
        'LQD': (80, 150),
        'GOLD': (1000, 5000),
    }

    # L3: Daily Change 임계값
    CHANGE_THRESHOLDS = {
        'VIX': 0.30,   # 30% - VIX는 변동성 큼
        'SPX': 0.05,   # 5%
        'DXY': 0.03,   # 3% - 환율은 상대적으로 안정
        'TNX': 0.10,   # 10%
        'HYG': 0.05,   # 5%
        'LQD': 0.03,   # 3%
        'GOLD': 0.05,  # 5%
    }

    # 필수 지표
    REQUIRED_METRICS = ['VIX', 'SPX', 'DXY', 'TNX']

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.data_cache = {}

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def fetch_data(self, target_date: str = None) -> Dict:
        """Yahoo Finance에서 데이터 수집"""
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        self.log(f"[DVSS] Fetching data from Yahoo Finance...")

        data = {}
        for name, symbol in self.SYMBOLS.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='5d')  # 5일치 가져옴

                if len(hist) >= 1:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) >= 2 else current
                    week_ago = hist['Close'].iloc[0] if len(hist) >= 5 else previous

                    change_pct = ((current - previous) / previous * 100) if previous else 0

                    data[name] = {
                        'current': round(current, 2),
                        'previous': round(previous, 2),
                        'week_ago': round(week_ago, 2),
                        'change_pct': round(change_pct, 2),
                        'source': f'Yahoo ({symbol})',
                        'valid': True
                    }
                    self.log(f"  ✅ {name}: {current:.2f} ({change_pct:+.2f}%)")
                else:
                    data[name] = {'valid': False, 'error': 'No data'}
                    self.log(f"  ❌ {name}: No data")

            except Exception as e:
                data[name] = {'valid': False, 'error': str(e)}
                self.log(f"  ❌ {name}: {e}")

        self.data_cache = data
        return data

    def validate(self, target_date: str = None, previous_data: Dict = None) -> DVSSReport:
        """
        4-Layer DVSS Validation

        Args:
            target_date: 검증 대상 날짜
            previous_data: 이전 bulletin 데이터 (L4용)

        Returns:
            DVSSReport
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        self.log(f"\n{'='*60}")
        self.log(f"  DVSS v2.0 - Data Validation")
        self.log(f"  Date: {target_date}")
        self.log(f"{'='*60}\n")

        # 데이터 수집
        data = self.fetch_data(target_date)

        issues = []
        warnings = []

        # ==========================================
        # L1: Completeness (20점)
        # ==========================================
        self.log("\n[L1] Completeness Check...")
        l1_score, l1_details = self._check_completeness(data)
        if l1_score < 20:
            issues.append(f"L1: Missing required data ({l1_score}/20)")

        # ==========================================
        # L2: Range (20점)
        # ==========================================
        self.log("\n[L2] Range Check...")
        l2_score, l2_details = self._check_range(data)
        if l2_score < 20:
            for metric, detail in l2_details.items():
                if detail.get('status') == 'FAIL':
                    issues.append(f"L2: {metric} out of range ({detail.get('value')})")

        # ==========================================
        # L3: Rate of Change (35점) - 핵심!
        # ==========================================
        self.log("\n[L3] Rate of Change Check...")
        l3_score, l3_details = self._check_rate_of_change(data)
        if l3_score < 35:
            for metric, detail in l3_details.items():
                if detail.get('status') == 'FAIL':
                    issues.append(f"L3: {metric} changed {detail.get('change')}% (threshold: ±{detail.get('threshold')}%)")
                elif detail.get('status') == 'WARN':
                    warnings.append(f"L3: {metric} changed {detail.get('change')}%")

        # ==========================================
        # L4: Cross-Validation (25점)
        # ==========================================
        self.log("\n[L4] Cross-Validation Check...")
        l4_score, l4_details = self._check_cross_validation(data, previous_data)
        if l4_score < 25:
            for metric, detail in l4_details.items():
                if isinstance(detail, dict) and detail.get('status') == 'FAIL':
                    issues.append(f"L4: {metric} cross-bulletin discrepancy")

        # ==========================================
        # 총점 계산
        # ==========================================
        total_score = l1_score + l2_score + l3_score + l4_score
        max_score = 100

        # Grade 결정
        if total_score >= 90:
            grade = DVSSGrade.A
            can_publish = True
        elif total_score >= 75:
            grade = DVSSGrade.B
            can_publish = True
        elif total_score >= 60:
            grade = DVSSGrade.C
            can_publish = False  # 수동 검토 필요
        else:
            grade = DVSSGrade.F
            can_publish = False

        self.log(f"\n{'='*60}")
        self.log(f"  DVSS RESULT: {total_score}/100 (Grade {grade.value})")
        self.log(f"  L1: {l1_score}/20 | L2: {l2_score}/20 | L3: {l3_score}/35 | L4: {l4_score}/25")
        self.log(f"  Can Publish: {'✅ YES' if can_publish else '❌ NO'}")
        self.log(f"{'='*60}\n")

        return DVSSReport(
            score=total_score,
            max_score=max_score,
            grade=grade,
            can_publish=can_publish,
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=l3_score,
            l4_score=l4_score,
            l1_details=l1_details,
            l2_details=l2_details,
            l3_details=l3_details,
            l4_details=l4_details,
            issues=issues,
            warnings=warnings
        )

    def _check_completeness(self, data: Dict) -> Tuple[int, Dict]:
        """L1: Completeness Check (20점)"""
        details = {}
        present = 0
        total = len(self.REQUIRED_METRICS)

        for metric in self.REQUIRED_METRICS:
            if metric in data and data[metric].get('valid', False):
                details[metric] = {'status': 'PASS', 'present': True}
                present += 1
                self.log(f"  ✅ {metric}: Present")
            else:
                details[metric] = {'status': 'FAIL', 'present': False}
                self.log(f"  ❌ {metric}: Missing")

        score = int((present / total) * 20)
        return score, details

    def _check_range(self, data: Dict) -> Tuple[int, Dict]:
        """L2: Range Check (20점)"""
        details = {}
        valid_count = 0
        total = 0

        for metric, (min_val, max_val) in self.VALID_RANGES.items():
            if metric not in data or not data[metric].get('valid', False):
                continue

            total += 1
            value = data[metric]['current']

            if min_val < value < max_val:
                details[metric] = {
                    'status': 'PASS',
                    'value': value,
                    'range': f"{min_val}-{max_val}"
                }
                valid_count += 1
                self.log(f"  ✅ {metric}: {value} (valid range: {min_val}-{max_val})")
            else:
                details[metric] = {
                    'status': 'FAIL',
                    'value': value,
                    'range': f"{min_val}-{max_val}"
                }
                self.log(f"  ❌ {metric}: {value} OUT OF RANGE ({min_val}-{max_val})")

        score = int((valid_count / total) * 20) if total > 0 else 0
        return score, details

    def _check_rate_of_change(self, data: Dict) -> Tuple[int, Dict]:
        """L3: Rate of Change Check (35점) - 핵심!"""
        details = {}
        valid_count = 0
        warn_count = 0
        total = 0

        for metric, threshold in self.CHANGE_THRESHOLDS.items():
            if metric not in data or not data[metric].get('valid', False):
                continue

            total += 1
            change_pct = abs(data[metric]['change_pct']) / 100  # 소수로 변환

            # 2x threshold = FAIL, 1x threshold = WARN
            if change_pct > threshold * 2:
                details[metric] = {
                    'status': 'FAIL',
                    'change': data[metric]['change_pct'],
                    'threshold': threshold * 100
                }
                self.log(f"  ❌ {metric}: {data[metric]['change_pct']:+.2f}% EXCEEDS {threshold*200:.0f}%")
            elif change_pct > threshold:
                details[metric] = {
                    'status': 'WARN',
                    'change': data[metric]['change_pct'],
                    'threshold': threshold * 100
                }
                warn_count += 1
                self.log(f"  ⚠️ {metric}: {data[metric]['change_pct']:+.2f}% (threshold: ±{threshold*100:.0f}%)")
            else:
                details[metric] = {
                    'status': 'PASS',
                    'change': data[metric]['change_pct'],
                    'threshold': threshold * 100
                }
                valid_count += 1
                self.log(f"  ✅ {metric}: {data[metric]['change_pct']:+.2f}%")

        # FAIL이 하나라도 있으면 0점, 그렇지 않으면 비례 점수
        fail_count = total - valid_count - warn_count
        if fail_count > 0:
            score = 0
        else:
            score = int(((valid_count + warn_count * 0.5) / total) * 35) if total > 0 else 0

        return score, details

    def _check_cross_validation(self, data: Dict, previous_data: Dict = None) -> Tuple[int, Dict]:
        """L4: Cross-Validation Check (25점)"""
        details = {}

        if previous_data is None:
            # 이전 데이터 없으면 기본 점수
            self.log("  ℹ️ No previous data for cross-validation")
            return 20, {'note': 'No previous data available'}

        valid_count = 0
        total = 0

        for metric in self.REQUIRED_METRICS:
            if metric not in data or not data[metric].get('valid', False):
                continue
            if metric not in previous_data:
                continue

            total += 1
            current = data[metric]['current']
            previous = previous_data.get(metric, {}).get('current', current)

            if previous == 0:
                continue

            change_pct = abs((current - previous) / previous)
            threshold = self.CHANGE_THRESHOLDS.get(metric, 0.10)

            # Cross-bulletin은 더 엄격하게 (2x 임계값까지 허용)
            if change_pct > threshold * 3:
                details[metric] = {
                    'status': 'FAIL',
                    'current': current,
                    'previous': previous,
                    'change': round(change_pct * 100, 2)
                }
                self.log(f"  ❌ {metric}: {previous} → {current} ({change_pct*100:.1f}% change)")
            else:
                details[metric] = {
                    'status': 'PASS',
                    'current': current,
                    'previous': previous,
                    'change': round(change_pct * 100, 2)
                }
                valid_count += 1
                self.log(f"  ✅ {metric}: {previous} → {current}")

        score = int((valid_count / total) * 25) if total > 0 else 20
        return score, details

    def get_validated_data(self) -> Dict:
        """검증된 데이터 반환"""
        return self.data_cache


# CLI 테스트
if __name__ == '__main__':
    import sys

    validator = DataValidator(verbose=True)

    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    report = validator.validate(date)

    print(f"\n=== DVSS Report ===")
    print(f"Score: {report.score}/{report.max_score}")
    print(f"Grade: {report.grade.value}")
    print(f"Can Publish: {report.can_publish}")
    print(f"Issues: {report.issues}")
    print(f"Warnings: {report.warnings}")
