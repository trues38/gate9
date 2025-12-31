# Edge Case Analysis: December 2024

## Overview

12월 20 거래일 중 **4건의 매크로-시장 불일치** 발견 (20%)

## Edge Cases

### 1. 2025-12-01: Risk-On + BTC Crash
- **Regime**: Goldilocks Reacceleration Anxiety
- **Risk Bias**: risk-on
- **Divergence**: BTC -4.5%, VIX +5.4%

**Analysis**:
- 레짐은 리스크온이지만 BTC가 크게 하락
- VIX도 상승하여 이중 불일치
- 원인 추정: 연말 레버리지 청산 + 달러 강세 압력

### 2. 2025-12-09: Risk-Off + BTC Rally
- **Regime**: Hawkish Cut Stalemate
- **Risk Bias**: risk-off
- **Divergence**: BTC +2.3%

**Analysis**:
- 레짐은 리스크오프인데 BTC 상승
- Gold도 +0.5%로 동반 상승
- 원인 추정: BTC가 "디지털 골드"로 인식되는 순간

### 3. 2025-12-17: Risk-On + VIX Spike
- **Regime**: Dovish Euphoria Amid War Premium
- **Risk Bias**: risk-on
- **Divergence**: VIX +6.9%

**Analysis**:
- 레짐 이름에 "War Premium" 포함 - 지정학 리스크
- 주식은 상승하는데 헷지 수요 급증
- 원인 추정: FOMC 직전 옵션 헷지 + 중동 리스크

### 4. 2025-12-23: Risk-On + Gold Rally
- **Regime**: Goldilocks Fed Pivot Anticipation
- **Risk Bias**: risk-on
- **Divergence**: Gold +1.3%

**Analysis**:
- 리스크온인데 Gold가 강세
- BTC는 -1.2%로 약세
- 원인 추정: 연말 안전자산 리밸런싱 + 달러 약세

## Edge Case Patterns

### Pattern A: BTC-Gold Decoupling
- BTC와 Gold가 반대 방향으로 움직이는 날: 12/1, 12/23
- **해석**: "디지털 골드" 내러티브가 불안정

### Pattern B: VIX-Regime Mismatch
- Risk-on 레짐인데 VIX 급등: 12/1, 12/17
- **해석**: 지정학/이벤트 리스크가 매크로를 압도

### Pattern C: Risk-Off + Risk Asset Rally
- Risk-off인데 BTC 상승: 12/9
- **해석**: 특정 조건에서 BTC가 안전자산화

## Recommendations

1. **레짐 판단 시 지정학 리스크 가중치 상향**
   - "War", "Geopolitical", "Crisis" 키워드 시 VIX 민감도 ↑

2. **BTC 판단 분리**
   - BTC는 리스크온/오프 이분법으로 분류 불가
   - 별도 BTC_REGIME 필드 추가 고려

3. **연말/분기말 특수 처리**
   - 12월 20일 이후 레버리지 청산 경고 추가

## Implementation

```python
def detect_edge_case(regime, econ_data):
    risk_bias = regime.get('risk_bias', 'unknown')
    mp = econ_data.get('market_prices', {})

    gold_chg = mp.get('Gold', {}).get('change_pct', 0)
    btc_chg = mp.get('Bitcoin', {}).get('change_pct', 0)
    vix_chg = mp.get('VIX', {}).get('change_pct', 0)

    warnings = []

    if risk_bias == 'risk-on':
        if gold_chg > 1.0:
            warnings.append(f"⚠️ EDGE: risk-on but Gold +{gold_chg:.1f}%")
        if btc_chg < -2.0:
            warnings.append(f"⚠️ EDGE: risk-on but BTC {btc_chg:.1f}%")
        if vix_chg > 5.0:
            warnings.append(f"⚠️ EDGE: risk-on but VIX +{vix_chg:.1f}%")

    elif risk_bias == 'risk-off':
        if btc_chg > 2.0:
            warnings.append(f"⚠️ EDGE: risk-off but BTC +{btc_chg:.1f}%")
        if gold_chg < -1.0:
            warnings.append(f"⚠️ EDGE: risk-off but Gold {gold_chg:.1f}%")

    return warnings
```

---
*Generated: 2025-12-30*
*Analysis Period: December 2024*
