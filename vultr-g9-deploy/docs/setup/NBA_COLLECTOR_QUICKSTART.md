# G9 NBA Collector - Quick Start Guide

## 🚀 Deploy in 5 Minutes

### Prerequisites
- VPS with 4GB RAM, Ubuntu 20.04+
- SSH access to VPS
- API Keys ready:
  - RapidAPI Key (Twitter241 API)
  - Neo4j password
  - N8N password

### Quick Deploy

```bash
# 1. Edit .env file with your API keys
nano .env

# 2. Run deployment script
./deploy_vps_nba.sh <YOUR_VPS_IP> root

# 3. Wait for deployment to complete
# ✓ Done! Services are running on your VPS
```

### Verify Deployment

```bash
# Check health
curl http://<VPS_IP>:8001/health

# Check budget (should show 500/500 calls available)
curl http://<VPS_IP>:8001/budget/status
```

## 📊 System Architecture

```
Twitter241 API (Free)     →    SQLite Storage    →    LLM Processing    →    Neo4j Graph
    500 calls/month            Deduplication         MiMo-V2-Flash (Free)      Relationships

                                      ↓

                                N8N Automation
                            (Time-based triggers)
```

## 🎯 API Budget Strategy

**Total: 500 calls/month**
- NBA: 250 calls (4 calls per game × ~60 games/month)
- Economy: 200 calls (5 sessions/day × 30 days = 150, with buffer)
- Test/Buffer: 50 calls

**Optimization Techniques:**
1. ✅ User ID Caching - Saves 1 call per username
2. ✅ Time-based Collection - Only before games/market hours
3. ✅ Deduplication - Prevents duplicate API calls
4. ✅ Batch Processing - Multiple accounts per call

## 🔑 Essential Commands

### On VPS (after SSH)

```bash
cd ~/g9-deploy

# View all container status
docker-compose ps

# View logs
docker-compose logs -f nba-collector

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Start all services
docker-compose up -d
```

### Remote API Calls (from anywhere)

```bash
# Health check
curl http://<VPS_IP>:8001/health

# Budget status
curl http://<VPS_IP>:8001/budget/status

# Storage stats
curl http://<VPS_IP>:8001/storage/stats

# Collect NBA tweets (manual trigger)
curl -X POST http://<VPS_IP>:8001/collect/nba

# Process tweets with LLM
curl -X POST http://<VPS_IP>:8001/process/llm \
  -H "Content-Type: application/json" \
  -d '{"domain": "nba", "batch_size": 50}'

# Full system status
curl http://<VPS_IP>:8001/status
```

## 🌐 Web Interfaces

| Service | URL | Login |
|---------|-----|-------|
| NBA Collector API | `http://<VPS_IP>:8001` | No auth |
| Neo4j Browser | `http://<VPS_IP>:7474` | neo4j / (from .env) |
| N8N Automation | `http://<VPS_IP>:5678` | admin / (from .env) |

## 📝 API Endpoints Reference

### GET Endpoints

- `/health` - Service health check
- `/budget/status` - Current API budget usage
- `/storage/stats` - Raw tweet storage statistics
- `/status` - Full system status

### POST Endpoints

- `/collect/nba` - Trigger NBA tweet collection
  ```json
  {
    "game_times": ["2025-12-28T19:00:00"]  // Optional
  }
  ```

- `/collect/economy` - Trigger economy tweet collection

- `/process/llm` - Process unprocessed tweets with LLM
  ```json
  {
    "domain": "nba",        // "nba" or "economy"
    "batch_size": 50        // tweets per batch
  }
  ```

## 🔍 Monitoring & Troubleshooting

### Check System Health

```bash
# Container health
docker-compose ps

# Memory usage
docker stats

# Disk usage
df -h

# View recent logs
docker-compose logs --tail=100 nba-collector
```

### Common Issues

**❌ "Container exited with code 1"**
```bash
# Check logs for error
docker-compose logs nba-collector

# Rebuild container
docker-compose up -d --build nba-collector
```

**❌ "API call failed"**
```bash
# Verify RAPIDAPI_KEY is set
docker-compose exec nba-collector env | grep RAPIDAPI

# Test API connection
docker-compose exec nba-collector python3 test_real_api.py
```

**❌ "Neo4j connection failed"**
```bash
# Check Neo4j is running
docker-compose ps neo4j-nba

# Restart Neo4j
docker-compose restart neo4j-nba
```

## 📦 Data Flow

1. **Collection** (API → Storage)
   - N8N triggers collection based on time
   - TwttrFreeAdapter fetches tweets from Twitter241 API
   - Raw tweets saved to SQLite (deduplication applied)
   - Budget tracking updated

2. **Processing** (Storage → LLM → Neo4j)
   - LLMProcessor extracts structured events from raw tweets
   - Events classified: INJURY, LINEUP, REFEREE, etc.
   - Entities extracted: Players, Teams, etc.
   - Events stored in Neo4j with relationships

3. **Analysis** (Neo4j → Insights)
   - Query player injury history
   - Find lineup patterns
   - Analyze referee impact
   - Generate betting insights

## 🎮 Test Collection

### Manual Test

```bash
# 1. SSH to VPS
ssh root@<VPS_IP>

# 2. Trigger collection
cd ~/g9-deploy
curl -X POST http://localhost:8001/collect/nba

# 3. Check results
curl http://localhost:8001/storage/stats

# 4. Process with LLM
curl -X POST http://localhost:8001/process/llm \
  -H "Content-Type: application/json" \
  -d '{"domain": "nba", "batch_size": 20}'

# 5. View in Neo4j
# Open browser: http://<VPS_IP>:7474
# Run query: MATCH (n) RETURN n LIMIT 25
```

## 📅 Automated Scheduling (N8N)

### Setup Workflows

1. Access N8N: `http://<VPS_IP>:5678`
2. Login: `admin` / (password from .env)
3. Import workflows:
   - NBA Collection: Runs T-2h, T-1h, T-30m, T-0 before games
   - Economy Collection: Runs 5x/day at market sessions
   - LLM Processing: Runs every 30 minutes for unprocessed tweets

### Workflow Triggers

**NBA Collection:**
- Check NBA schedule API for today's games
- For each game, trigger 4 collections:
  - T-2h: Injury/referee updates
  - T-1h: Lineup confirmations
  - T-30m: Last-minute changes
  - T-0: Final check

**Economy Collection:**
- 08:00 KST - Pre-market Asia
- 16:00 KST - Pre-market US
- 22:30 KST - Market open US
- 01:00 KST - Mid-market
- 05:00 KST - Market close + after-hours

## 💰 Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Twitter API | $0.00/month | RapidAPI Free (500 calls) |
| LLM Processing | $0.00/month | MiMo-V2-Flash free tier |
| VPS (4GB RAM) | $5-10/month | Vultr, DigitalOcean, etc. |
| **Total** | **$5-10/month** | VPS cost only |

## 🔐 Security Checklist

- [ ] Change default Neo4j password
- [ ] Change N8N admin password
- [ ] Set firewall rules (only allow ports 7474, 7687, 5678, 8001)
- [ ] Use strong passwords in .env
- [ ] Keep .env file secure (never commit to git)
- [ ] Regular backups of SQLite and Neo4j databases
- [ ] Monitor API usage to prevent quota exhaustion

## 📈 Next Steps

1. ✅ Deploy to VPS
2. ✅ Verify all services running
3. ⬜ Import N8N workflows
4. ⬜ Configure automated triggers
5. ⬜ Set up monitoring/alerts
6. ⬜ Test full end-to-end flow
7. ⬜ Schedule regular backups

## 🆘 Support

**Logs Location:**
- Container logs: `docker-compose logs -f <service>`
- NBA Collector: `~/g9-deploy/nba-collector/logs/`
- Neo4j logs: Docker volume `neo4j_nba_logs`

**Health Checks:**
- API: `http://<VPS_IP>:8001/health`
- Neo4j: `http://<VPS_IP>:7474`
- N8N: `http://<VPS_IP>:5678`

**Budget Monitoring:**
```bash
# Check usage
curl http://<VPS_IP>:8001/budget/status | python3 -m json.tool

# Expected output:
{
  "monthly_limit": 500,
  "total_used": 0,
  "remaining": 500,
  "nba_budget": 250,
  "nba_used": 0,
  "economy_budget": 200,
  "economy_used": 0
}
```
