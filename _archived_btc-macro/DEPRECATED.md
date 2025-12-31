# DEPRECATED - 이 폴더는 더 이상 사용되지 않습니다

## 마이그레이션 완료: 2024-12-30

BTC Macro 코드가 regime_zero로 통합되었습니다.

### 새 위치
```
/Users/js/g9/regime_zero/btc_macro/
```

### 왜 통합했나?
- BTC Macro는 경제 레짐 기반 Law 실행 엔진
- regime_zero와 레짐 데이터/파이프라인 공유
- 중복 제거 및 유지보수 편의성

### 이 폴더 삭제 가능?
- 데이터 백업 확인 후 삭제 가능
- `regime_objects.jsonl`은 심볼릭 링크로 연결됨

### 참고 문서
- 정체성 정의: `regime_zero/btc_macro/MANIFESTO.md`
- 프로젝트 상태: `regime_zero/btc_macro/PROJECT_STATUS.md`
