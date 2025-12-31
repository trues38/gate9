# Economic Regime State Graph Engine

**If you return a normal economic report, you have failed.**

## 철학

이건 리포트 생성기가 아니다.
이건 **상태 공간 탐색 엔진**이다.

- Regime은 라벨이 아니라 **State Node**
- Event는 저장용이 아니라 **Shock Node**
- 결과는 정답이 아니라 **Weight Update Trigger**

## 핵심 원칙

1. **동시 다발 Regime**: 같은 날에 여러 Regime이 활성화될 수 있다
2. **구조적 Twin**: 날짜가 아닌 서브그래프 동형성으로 유사성 탐색
3. **경로 출력**: "추천"이 아닌 "전이 확률 경로"

---

*© 2025 G9 Regime Zero - State Graph Engine*
