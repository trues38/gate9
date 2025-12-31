# VPS에 /tweets/recent Endpoint 추가하기

## 방법 1: Vultr 웹 터미널에서 직접 수정

### 1. Vultr 대시보드 접속
- https://my.vultr.com/ 로그인
- 서버 141.164.35.214 선택
- 우측 상단 "View Console" 클릭

### 2. raw_storage.py 수정

```bash
cd /opt/g9/domains/nba/collector/storage

# 백업
cp raw_storage.py raw_storage.py.backup

# 편집 (nano 사용)
nano raw_storage.py
```

**추가할 내용** (Line 298 위치, `def get_stats()` 함수 바로 위에):

```python
    def get_recent_tweets(
        self,
        domain: Optional[str] = None,
        limit: int = 10,
        include_processed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent tweets (for debugging/inspection)

        Args:
            domain: Filter by domain ("nba" or "economy")
            limit: Maximum tweets to return
            include_processed: Include already processed tweets

        Returns:
            List of tweet dicts with all fields
        """
        query = "SELECT * FROM raw_tweets WHERE 1=1"
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if not include_processed:
            query += " AND processed = 0"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        tweets = []
        for row in cursor.fetchall():
            tweets.append(dict(row))

        logger.info(f"Retrieved {len(tweets)} recent tweets")
        return tweets
```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

### 3. app_api.py 수정

```bash
cd /opt/g9/domains/nba/collector

# 백업
cp app_api.py app_api.py.backup

# 편집
nano app_api.py
```

**추가할 내용** (Line 115 위치, `/status` endpoint 바로 위에):

```python
@app.route('/tweets/recent', methods=['GET'])
def recent_tweets():
    """Get recent tweets for inspection"""
    try:
        domain = request.args.get('domain', None)
        limit = int(request.args.get('limit', 10))
        include_processed = request.args.get('include_processed', 'true').lower() == 'true'

        tweets = pipeline.raw_storage.get_recent_tweets(
            domain=domain,
            limit=limit,
            include_processed=include_processed
        )
        return jsonify({
            "tweets": tweets,
            "count": len(tweets)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

### 4. 컨테이너 재시작

```bash
cd /opt/g9
docker compose restart nba-collector
```

### 5. 테스트

```bash
# 최근 트윗 확인
curl "http://localhost:8001/tweets/recent?domain=nba&limit=5"
```

---

## 방법 2: 로컬에서 파일 복사 (SSH 비밀번호 필요)

```bash
cd /Users/js/g9/vultr-g9-deploy

# 파일 복사
scp domains/nba/collector/storage/raw_storage.py root@141.164.35.214:/opt/g9/domains/nba/collector/storage/
scp domains/nba/collector/app_api.py root@141.164.35.214:/opt/g9/domains/nba/collector/

# 재시작
ssh root@141.164.35.214 "cd /opt/g9 && docker compose restart nba-collector"
```

---

## 사용 예시

업데이트 완료 후:

```bash
# NBA 도메인 최근 트윗 5개
curl "http://141.164.35.214:8001/tweets/recent?domain=nba&limit=5"

# 모든 도메인 최근 10개
curl "http://141.164.35.214:8001/tweets/recent?limit=10"

# 미처리 트윗만
curl "http://141.164.35.214:8001/tweets/recent?include_processed=false"
```

응답 형식:
```json
{
  "count": 2,
  "tweets": [
    {
      "id": 1,
      "tweet_id": "12345",
      "username": "ShamsCharania",
      "text": "LeBron James (ankle) is OUT tonight...",
      "created_at": "2025-12-28T10:30:00",
      "domain": "nba",
      "processed": 1
    }
  ]
}
```
