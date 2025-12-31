#!/bin/bash
# 1분마다 Event 수 확인

echo "=== Event 증가 모니터링 (Ctrl+C로 종료) ==="
echo ""

while true; do
  COUNT=$(curl -s -u neo4j:regime2025 -X POST http://localhost:7475/db/neo4j/tx/commit \
    -H "Content-Type: application/json" \
    -d '{"statements":[{"statement":"MATCH (e:Event) WHERE e.event_id STARTS WITH '\''evt_'\'' RETURN count(e) as count"}]}' \
    | jq -r '.results[0].data[0].row[0]')
  
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TIMESTAMP] Total Events: $COUNT"
  
  sleep 60
done
