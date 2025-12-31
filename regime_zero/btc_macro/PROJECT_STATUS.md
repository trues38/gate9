# BTC Macro Engine

## Law Registry v1.0 (2024-12-28)

### 유효한 Laws (전통자산)
```
✅ TLT_TECH:         TLT +2% → XLK (5d lag, 10d hold)    OOS 94%, p<0.01
✅ VIX_CREDIT:       VIX spike → HYG short (3d, 7d)     OOS 73%, p=0.03
✅ REAL_RATES_GOLD:  TIP +1.5% → GLD (3d lag, 7d hold)  OOS 89%, p=0.02
```

### BTC ETF 시대 새 Law (2024+)
```
✅ ETF_ACCUMULATION: IBIT Vol >1.3x + BTC Down >2% → Long BTC
   - Full: N=11, WR=73%, Avg=+4.79%
   - H2 2024 OOS: N=6, WR=100%, p=0.016 ✅
   - Exit: TP +7% / SL -5% / Time 10d
   - 메커니즘: 기관 ETF 딥 매수 → 5-10일 내 가격 반영
```

### GOLD_BTC Law: 2024 구조적 변화
```
⚠️ GOLD_BTC: Gold +3% → BTC (5d lag, 7d hold) - DEPRECATED
   - 2024년 단독: 38% WR (구조 변화로 무효화)
   - 대체: ETF_ACCUMULATION 사용
```

## 프로젝트 구조
```
/btc-macro
├── src/btc_engine/
│   ├── experiments/     # 가설 테스트 코드
│   ├── strategies/      # 검증된 전략
│   ├── validation/      # CP-8~11 검증
│   └── core/            # 핵심 엔진
├── data/
│   ├── regime_families.json   # 13개 레짐 패밀리
│   └── regime_objects.jsonl   # 20,000개 상태 벡터
└── logs/
```

## Law Validation Summary

| Law | In-Sample | OOS | Status |
|-----|-----------|-----|--------|
| **ETF_ACCUMULATION** | 73% | 100% (H2) | ✅ **NEW BTC Law** |
| TLT_TECH | 89% | 94% | ✅ Active |
| VIX_CREDIT | 73% | 73% | ✅ Active |
| REAL_RATES_GOLD | 73% | 89% | ✅ Active |
| GOLD_BTC | 57.9% | 50.0% | ⚠️ Deprecated |
| YEN_CARRY | 69% | N<3 | ❌ Rejected |
| YIELD_CURVE | 60% | 33% | ❌ Rejected |
| ENERGY_SHOCK | 88% | N<3 | ❌ Rejected |

## 운용 규칙
1. 포지션 사이즈: 5-10%
2. 레짐: Gold Safe-Haven에서만 H7 활성화
3. 연패 관리: 3연패 시 사이즈 50% 축소
4. 월간 손실 한도: -10% 도달 시 월말까지 중단

## Next Steps

### Option A: 전통자산 운용
- TLT_TECH, VIX_CREDIT, REAL_RATES_GOLD 3개 Law로 운용
- BTC 제외, 전통 ETF만 (XLK, HYG, GLD)
- 안정적이지만 BTC 업사이드 포기

### Option B: BTC ETF 시대 적응
- 새로운 BTC 신호 탐색 필요
- 후보: ETF Flow, Funding Rate, Basis
- 2024 이후 데이터로 재검증 필요

### Option C: Hybrid
- 전통자산 Law 운용 + BTC 모니터링
- BTC는 관망 후 새 패턴 발견 시 재진입

---
Last Updated: 2024-12-28
Law Registry v1.0 완성
GOLD_BTC 2024 구조 변화 발견
