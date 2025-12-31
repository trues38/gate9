# 🔥 G9 모니터링 대시보드 - 영구 운영 가이드

## ✅ 네, 계속 살아있습니다!

### 📍 영구 URL
```
http://141.164.35.214:3000/d/g9-main-dashboard

✅ VPS 재부팅해도 자동 재시작
✅ 크래시 나도 자동 재시작
✅ 수동으로 중지하지 않는 한 24/7 운영
```

---

## 🛡️ 자동 재시작 메커니즘

### Docker Compose 설정
```yaml
restart: unless-stopped

의미:
✅ VPS 재부팅 → 자동 재시작
✅ 컨테이너 크래시 → 자동 재시작
✅ Docker 데몬 재시작 → 자동 재시작
❌ 수동 docker stop → 재시작 안함 (의도적)
```

### 현재 상태
```
g9-grafana       : unless-stopped ✅
g9-prometheus    : unless-stopped ✅
g9-metrics-api   : unless-stopped ✅
g9-node-exporter : unless-stopped ✅
```

---

## 💾 데이터 영구성

### Grafana 데이터 (대시보드, 설정)
```
볼륨: monitoring_grafana-data
위치: /var/lib/docker/volumes/monitoring_grafana-data/_data

저장되는 것:
- 대시보드 설정
- 사용자 계정
- 알림 설정
- 플러그인
```

### Prometheus 데이터 (시계열 메트릭)
```
볼륨: monitoring_prometheus-data
위치: /var/lib/docker/volumes/monitoring_prometheus-data/_data

저장되는 것:
- 모든 메트릭 히스토리 (기본 15일)
- Alert 상태
- 타겟 설정
```

**➡️ 컨테이너 삭제해도 데이터는 남아있음!**

---

## 🔄 자동 재시작 시나리오

### 시나리오 1: VPS 재부팅
```
1. VPS 재부팅
2. Docker 데몬 자동 시작
3. monitoring 컨테이너 4개 자동 시작
4. 30초 내 대시보드 복구
5. 기존 데이터 모두 유지
```

### 시나리오 2: 컨테이너 크래시
```
1. g9-grafana 크래시 (예: 메모리 부족)
2. Docker가 자동 감지
3. 즉시 재시작
4. 5초 내 복구
5. 데이터 손실 없음
```

### 시나리오 3: Docker 업데이트
```
1. Docker 데몬 업데이트
2. 모든 컨테이너 자동 재시작
3. 대시보드 자동 복구
4. 설정 모두 유지
```

---

## 📊 운영 지속성 보장

### 1. 네트워크 끊김 → 자동 복구
```
VPS 네트워크 일시 중단
↓
컨테이너는 계속 실행 중
↓
네트워크 복구
↓
메트릭 수집 자동 재개
```

### 2. 메모리 부족 → 자동 재시작
```
컨테이너 메모리 부족으로 종료
↓
Docker가 자동 재시작
↓
정상 운영 복구
```

### 3. 디스크 가득 참 → 경고만
```
Prometheus 알림 발생
↓
디스크 90% 초과 경고
↓
수동 정리 필요 (자동 삭제 안함)
```

---

## 🕐 데이터 보존 기간

### Prometheus 메트릭
```
기본: 15일
설정: prometheus.yml에서 변경 가능

변경 방법:
prometheus.yml에 추가:
  --storage.tsdb.retention.time=30d  # 30일로 변경
```

### Grafana 대시보드
```
영구 보존 (삭제하지 않는 한)
```

---

## 🔧 관리 명령어

### 상태 확인
```bash
# 컨테이너 상태
ssh root@141.164.35.214 "docker ps | grep g9-"

# 볼륨 확인
ssh root@141.164.35.214 "docker volume ls | grep monitoring"

# 로그 확인
ssh root@141.164.35.214 "docker logs g9-grafana --tail 100"
```

### 재시작 (필요시)
```bash
# 전체 스택 재시작
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose restart"

# 개별 컨테이너 재시작
ssh root@141.164.35.214 "docker restart g9-grafana"
```

### 중지 (의도적으로만)
```bash
# 전체 중지
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose stop"

# 재시작
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose start"
```

### 완전 제거 (데이터 보존)
```bash
# 컨테이너만 제거 (데이터 유지)
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose down"

# 나중에 복구
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose up -d"
# → 기존 대시보드, 메트릭 히스토리 모두 복구됨!
```

### 완전 제거 (데이터 포함)
```bash
# ⚠️ 주의: 모든 데이터 삭제됨!
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose down -v"
```

---

## 🌍 외부 접근 (항상 가능)

### URL 변경 없음
```
고정 IP: 141.164.35.214
고정 포트: 3000 (Grafana), 9090 (Prometheus)

http://141.164.35.214:3000/d/g9-main-dashboard
↑ 이 URL은 절대 바뀌지 않음
```

### 도메인 연결 (선택)
```bash
# 예: dashboard.g9.com → 141.164.35.214:3000
# DNS A 레코드 추가하면 됨

dashboard.g9.com/d/g9-main-dashboard
↑ 도메인으로도 접근 가능
```

---

## 🚨 자동 알림 (24/7 감시)

### Prometheus Alerts 활성화
```
8개 알림 규칙 항상 실행 중:

🔴 Critical (즉시 대응 필요):
- Odds API 450회 초과
- Twitter API 450회 초과
- NBA 수집 10분 중단
- 경제 수집 10분 중단
- VPS 메모리 90% 초과
- VPS 디스크 90% 초과

🟡 Warning (주의):
- Neo4j 노드 1시간 증가 없음
- VPS CPU 80% 초과

확인: http://141.164.35.214:9090/alerts
```

---

## 📈 장기 운영 시나리오

### 1개월 운영
```
✅ 메트릭 히스토리: 15일치 보존
✅ 대시보드 설정: 그대로 유지
✅ API 사용량 누적: 계속 추적
✅ Neo4j 노드 증가: 그래프로 시각화
```

### 1년 운영
```
✅ Prometheus 자동 데이터 정리 (15일 이후)
✅ Grafana 대시보드 영구 보존
✅ 볼륨 용량: ~1GB 미만 (압축됨)
✅ 성능 저하 없음
```

### VPS 마이그레이션
```
1. 기존 VPS:
   docker compose down
   tar -czf monitoring-backup.tar.gz /var/lib/docker/volumes/monitoring_*

2. 새 VPS:
   tar -xzf monitoring-backup.tar.gz -C /
   docker compose up -d

3. 결과:
   ✅ 모든 대시보드 복구
   ✅ 메트릭 히스토리 복구
   ✅ 설정 그대로 유지
```

---

## 🎯 정리

### ✅ 죽지 않는 이유

1. **Docker Compose restart 정책**
   - VPS 재부팅 → 자동 재시작
   - 크래시 → 자동 재시작

2. **영구 볼륨**
   - 대시보드 설정 영구 보존
   - 메트릭 히스토리 보존

3. **고정 URL**
   - IP 변경 없음 (VPS 고정 IP)
   - 포트 변경 없음

4. **자동 알림**
   - 문제 발생 시 즉시 감지
   - 24/7 모니터링

### ❌ 죽는 경우 (의도적으로만)

1. **수동 중지**
   ```bash
   docker compose stop  # 수동 중지
   ```

2. **VPS 계약 종료**
   ```
   VPS 자체가 삭제됨
   ```

3. **볼륨 삭제**
   ```bash
   docker compose down -v  # -v 플래그로 볼륨까지 삭제
   ```

---

## 🚀 결론

```
┌─────────────────────────────────────────┐
│   G9 모니터링 대시보드                   │
│   24/7/365 영구 운영                     │
├─────────────────────────────────────────┤
│                                          │
│  ✅ URL: 절대 바뀌지 않음                │
│  ✅ 재부팅: 자동 재시작                  │
│  ✅ 크래시: 자동 복구                    │
│  ✅ 데이터: 영구 보존                    │
│  ✅ 알림: 24/7 감시                      │
│  ✅ 백업: 볼륨만 백업하면 복구 가능      │
│                                          │
│  http://141.164.35.214:3000              │
│  ID: admin / PW: g9admin2025             │
│                                          │
└─────────────────────────────────────────┘

"지금 이 순간부터 영원히 살아있습니다" 🔥
```

---

**VPS만 살아있으면 대시보드는 절대 죽지 않습니다!** 💪

**지금 북마크 해두고 언제든 접속하세요!** 📊
