#!/usr/bin/env python3
"""
G9 Unified Bulletin Pipeline v1.1
==================================
DVSS → State Engine → Bulletin Generator
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UnifiedPipeline:
    """Unified Pipeline: Yahoo Finance → Validation → Bulletin"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def run(self, date: str = None) -> Dict:
        """
        Full pipeline execution:
        1. Fetch data from Yahoo Finance
        2. Validate data
        3. Calculate states
        4. Return unified result
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        self.log(f"\n{'='*65}")
        self.log(f"  UNIFIED PIPELINE v1.1 (Asia Layer)")
        self.log(f"  Date: {date}")
        self.log(f"{'='*65}\n")

        # Step 1: Fetch data
        self.log("[STEP 1] Fetching market data...")
        data = self._fetch_data()

        if not data:
            return {"success": False, "error": "Failed to fetch data"}

        # Step 2: Validate
        self.log("[STEP 2] Validating data...")
        validation = self._validate_data(data)

        # Step 3: Calculate states
        self.log("[STEP 3] Calculating states...")
        states = self._calculate_states(data)

        return {
            "success": True,
            "date": date,
            "data": data,
            "validation": validation,
            "states": states
        }

    def _fetch_data(self) -> Dict:
        """Fetch data from Yahoo Finance"""
        symbols = {
            '^VIX': 'VIX',
            '^GSPC': 'SPX',
            'GC=F': 'GOLD',
            '^TNX': 'TNX',
            'DX-Y.NYB': 'DXY',
            'KRW=X': 'USDKRW',
            '^KS11': 'KOSPI',
            'JPY=X': 'USDJPY',
            '^N225': 'NIKKEI'
        }

        data = {}
        for ticker, name in symbols.items():
            try:
                df = yf.Ticker(ticker).history(period='2d')
                if len(df) >= 1:
                    current = df['Close'].iloc[-1]
                    prev = df['Close'].iloc[-2] if len(df) >= 2 else current
                    change_pct = ((current - prev) / prev * 100) if prev else 0
                    data[name] = {
                        'current': round(current, 2),
                        'previous': round(prev, 2),
                        'change_pct': round(change_pct, 2)
                    }
            except Exception as e:
                self.log(f"  ⚠️ {name} failed: {e}")

        return data

    def _validate_data(self, data: Dict) -> Dict:
        """Simple DVSS validation"""
        score = 0
        max_score = 0
        issues = []

        # L1: Completeness
        required = ['VIX', 'SPX', 'DXY']
        completeness = sum(1 for k in required if k in data) / len(required) * 25
        score += completeness
        max_score += 25

        # L2: Range check
        ranges = {
            'VIX': (9, 80),
            'DXY': (70, 130),
            'SPX': (3000, 10000)
        }
        range_score = 0
        for key, (min_val, max_val) in ranges.items():
            if key in data:
                val = data[key]['current']
                if min_val < val < max_val:
                    range_score += 1
        range_score = (range_score / len(ranges)) * 25
        score += range_score
        max_score += 25

        # L3: Rate of change
        change_score = 0
        thresholds = {'VIX': 30, 'DXY': 3, 'SPX': 5}
        for key, threshold in thresholds.items():
            if key in data:
                if abs(data[key]['change_pct']) < threshold:
                    change_score += 1
                else:
                    issues.append(f"{key} changed {data[key]['change_pct']}%")
        change_score = (change_score / len(thresholds)) * 35
        score += change_score
        max_score += 35

        # L4: Cross-validation (skip for now)
        max_score += 15

        total_score = int(score)
        grade = 'A' if total_score >= 90 else 'B' if total_score >= 75 else 'C' if total_score >= 60 else 'F'
        can_publish = grade in ['A', 'B']

        return {
            'score': total_score,
            'max_score': max_score,
            'grade': grade,
            'can_publish': can_publish,
            'issues': issues
        }

    def _calculate_states(self, data: Dict) -> Dict:
        """Calculate market states"""
        states = {}

        # VIX-based risk appetite
        if 'VIX' in data:
            vix = data['VIX']['current']
            if vix < 15:
                states['RISK_APPETITE_EXPANSION'] = round(1.0 - (vix - 12) / (15 - 12) * 0.2, 2)
                states['RISK_APPETITE_SUPPRESSED'] = 0.04
            elif vix > 25:
                states['RISK_APPETITE_SUPPRESSED'] = round((vix - 25) / (35 - 25) * 0.8, 2)
                states['RISK_APPETITE_EXPANSION'] = 0.04
            else:
                states['RISK_APPETITE_EXPANSION'] = 0.50
                states['RISK_APPETITE_SUPPRESSED'] = 0.50

        # DXY-based dollar tightening
        if 'DXY' in data:
            dxy = data['DXY']['current']
            if dxy > 100:
                states['DOLLAR_LIQUIDITY_TIGHTENING'] = round((dxy - 100) / (105 - 100) * 0.6, 2)
            else:
                states['DOLLAR_LIQUIDITY_TIGHTENING'] = 0.10

        # Other states (default low)
        states['YIELD_CURVE_INVERSION'] = 0.00
        states['DELEVERAGING_PRESSURE'] = 0.06
        states['LIQUIDITY_STRESS'] = 0.04

        return states


def _build_bulletin_from_result(result: Dict) -> str:
    """Build bulletin markdown from result"""
    data = result.get('data', {})
    validation = result.get('validation', {})
    states = result.get('states', {})
    date = result.get('date', datetime.now().strftime("%Y-%m-%d"))

    # Find dominant state
    dominant_states = {k: v for k, v in states.items() if v >= 0.5}
    dominant_state = max(states.items(), key=lambda x: x[1])[0] if states else 'NONE'

    # US Data
    us_data_rows = []
    us_symbols = ['VIX', 'SPX', 'GOLD', 'TNX', 'DXY']
    for sym in us_symbols:
        if sym in data:
            us_data_rows.append(
                f"| {sym} | {data[sym]['current']} | {data[sym]['change_pct']:+.2f}% |"
            )

    # Asia Data
    asia_data_rows = []
    asia_symbols = {'USDKRW': '🇰🇷 USD/KRW', 'KOSPI': '🇰🇷 KOSPI',
                    'USDJPY': '🇯🇵 USD/JPY', 'NIKKEI': '🇯🇵 Nikkei'}
    for sym, label in asia_symbols.items():
        if sym in data:
            asia_data_rows.append(
                f"| {label} | {data[sym]['current']} | {data[sym]['change_pct']:+.2f}% |"
            )

    # States table
    state_rows = []
    for state, intensity in sorted(states.items(), key=lambda x: x[1], reverse=True):
        signal = '🟢' if intensity < 0.3 else '🟡' if intensity < 0.6 else '🔴'
        state_rows.append(f"| {state} | {intensity:.2f} | {signal} |")

    bulletin = f"""# G9 GLOBAL ECONOMIC BULLETIN

| | |
|---|---|
| **Date** | {date} |
| **Engine** | Unified Pipeline v1.1 (Asia Layer) |
| **DVSS Score** | {validation.get('score', 0)}/100 (Grade {validation.get('grade', 'N/A')}) |

---

## 🛡️ DATA VALIDATION

**Publication:** {'✅ APPROVED' if validation.get('can_publish') else '❌ BLOCKED'}

---

## 🇺🇸 US MARKET DATA

| Indicator | Value | Daily Δ |
|-----------|-------|---------|
{''.join(us_data_rows)}

---

## 🌏 ASIA MARKET DATA

| Market | Value | Daily Δ |
|--------|-------|---------|
{''.join(asia_data_rows)}

---

## 🔍 STATE ANALYSIS

**Dominant State:** {dominant_state}

| State | Intensity | Signal |
|-------|-----------|--------|
{''.join(state_rows)}

---

## 📋 SUMMARY

**오늘의 판단:** {'Risk-On' if 'EXPANSION' in dominant_state else 'Risk-Off' if 'SUPPRESSED' in dominant_state else 'Neutral'}

---

*Generated by Unified Pipeline v1.1*
*{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    return bulletin
