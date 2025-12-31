# G9 NBA Collector - VPS Deployment Guide

## System Overview

**Free Twitter Data Collection System**
- Twitter241 API (RapidAPI Free: 500 calls/month)
- SQLite raw storage
- MiMo-V2-Flash LLM processing (free via OpenRouter)
- Neo4j graph database
- N8N workflow automation

## Budget Allocation
- **NBA**: 250 calls/month
- **Economy**: 200 calls/month
- **Buffer**: 50 calls/month

## API Calls Strategy
- NBA: Event-based (T-2h, T-1h, T-30m, T-0 before games)
- Economy: Session-based (5 times/day at market hours)
- User ID caching to save calls

## Prerequisites

1. **VPS Requirements**
   - 4 GB RAM minimum
   - 20 GB disk space
   - Docker & Docker Compose installed
   - Ubuntu 20.04+ or similar Linux distro

2. **API Keys Required**
   - RapidAPI Key (for Twitter241 API)
   - OpenRouter API Key (optional, will use mock mode if not set)
   - XAI API Key (for N8N workflows)

3. **Environment Variables**
   ```bash
   RAPIDAPI_KEY=your_rapidapi_key_here
   RAPIDAPI_PROVIDER=twttr-api-free
   OPENROUTER_API_KEY=your_openrouter_key_here
   NEO4J_NBA_USERNAME=neo4j
   NEO4J_NBA_PASSWORD=your_secure_password
   N8N_USER=admin
   N8N_PASSWORD=your_n8n_password
   XAI_API_KEY=your_xai_key
   ```

## Deployment Steps

### Step 1: Prepare VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
```

### Step 2: Upload Project Files

From your local machine:

```bash
# Navigate to project directory
cd /Users/js/g9/vultr-g9-deploy

# Copy files to VPS (replace with your VPS IP)
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
  . user@your-vps-ip:~/g9-deploy/
```

Or use the deployment script:

```bash
# Make deployment script executable
chmod +x deploy_vps.sh

# Run deployment (will prompt for VPS IP)
./deploy_vps.sh
```

### Step 3: Configure Environment

On VPS:

```bash
cd ~/g9-deploy

# Create .env file
cp .env.example .env

# Edit with your actual keys
nano .env
```

Required .env variables:
```bash
# Twitter API (RapidAPI)
RAPIDAPI_KEY=d9fa80a403msh90d42ea87aedfbap1b38e0jsn61919080729d
RAPIDAPI_PROVIDER=twttr-api-free

# LLM Processing (OpenRouter - optional)
OPENROUTER_API_KEY=

# Neo4j NBA
NEO4J_NBA_USERNAME=neo4j
NEO4J_NBA_PASSWORD=your_secure_password_here
NEO4J_NBA_HEAP_INIT=512M
NEO4J_NBA_HEAP_MAX=1G
NEO4J_NBA_PAGECACHE=512M

# N8N
N8N_USER=admin
N8N_PASSWORD=your_n8n_password_here
N8N_MEMORY=1G
XAI_API_KEY=your_xai_key_here

# (Economy Neo4j settings omitted for brevity)
```

### Step 4: Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f nba-collector
```

Expected output:
```
NAME                  STATUS              PORTS
g9-neo4j-nba          running             7474:7474, 7687:7687
g9-nba-collector      running (healthy)   8001:8001
g9-n8n                running             5678:5678
```

### Step 5: Verify Deployment

1. **Check NBA Collector API**
   ```bash
   curl http://localhost:8001/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "G9 NBA Collector (Free Pipeline)",
     "version": "3.0.0"
   }
   ```

2. **Check Budget Status**
   ```bash
   curl http://localhost:8001/budget/status
   ```

3. **Check Storage Stats**
   ```bash
   curl http://localhost:8001/storage/stats
   ```

4. **Access Neo4j Browser**
   - URL: `http://your-vps-ip:7474`
   - Username: `neo4j`
   - Password: (from .env)

5. **Access N8N**
   - URL: `http://your-vps-ip:5678`
   - Username: `admin`
   - Password: (from .env)

### Step 6: Test Collection

```bash
# Test NBA collection
curl -X POST http://localhost:8001/collect/nba \
  -H "Content-Type: application/json" \
  -d '{}'

# Test Economy collection
curl -X POST http://localhost:8001/collect/economy

# Process tweets with LLM
curl -X POST http://localhost:8001/process/llm \
  -H "Content-Type: application/json" \
  -d '{"domain": "nba", "batch_size": 50}'
```

## N8N Workflow Setup

1. Access N8N at `http://your-vps-ip:5678`
2. Login with N8N_USER and N8N_PASSWORD
3. Import workflows from `n8n_workflows/` directory:
   - NBA Collection Workflow (runs before games)
   - Economy Collection Workflow (runs at market sessions)
   - LLM Processing Workflow (processes unprocessed tweets)

## Monitoring

### Check Container Health
```bash
docker-compose ps
docker stats
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f nba-collector

# Last 100 lines
docker-compose logs --tail=100 nba-collector
```

### Database Stats
```bash
# NBA Collector storage
curl http://localhost:8001/storage/stats

# API budget status
curl http://localhost:8001/budget/status

# Full system status
curl http://localhost:8001/status
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs nba-collector

# Restart service
docker-compose restart nba-collector

# Rebuild if needed
docker-compose up -d --build nba-collector
```

### API Connection Issues

```bash
# Check RAPIDAPI_KEY is set correctly
docker-compose exec nba-collector env | grep RAPIDAPI

# Test API directly
docker-compose exec nba-collector python3 -c "
import os
from sources.twttr_free_adapter import TwttrFreeAdapter
adapter = TwttrFreeAdapter()
print(f'Mock mode: {adapter.mock_mode}')
print(f'API host: {adapter.API_HOST}')
"
```

### Neo4j Connection Issues

```bash
# Check Neo4j is running
docker-compose ps neo4j-nba

# Check connection from collector
docker-compose exec nba-collector python3 -c "
from neo4j import GraphDatabase
uri = 'bolt://neo4j-nba:7687'
driver = GraphDatabase.driver(uri, auth=('neo4j', 'password'))
driver.verify_connectivity()
print('✓ Connected')
"
```

### Reset Everything

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## Maintenance

### Monthly Tasks

1. **Reset API call counters** (on 1st of each month)
   ```bash
   # Will be automated via N8N workflow
   curl -X POST http://localhost:8001/admin/reset-budget
   ```

2. **Backup databases**
   ```bash
   # SQLite backup
   docker-compose exec nba-collector cp data/raw_tweets.db data/backup/raw_tweets_$(date +%Y%m%d).db

   # Neo4j backup
   docker-compose exec neo4j-nba neo4j-admin database dump neo4j --to=/data/backup/neo4j_$(date +%Y%m%d).dump
   ```

3. **Review budget usage**
   ```bash
   curl http://localhost:8001/budget/status
   ```

## Budget Optimization Tips

1. **Use user ID caching** - Already implemented, saves 1 call per username
2. **Time-based collection** - Only collect before games/market hours
3. **Batch processing** - Process multiple tweets with LLM in one go
4. **Deduplication** - Raw storage prevents duplicate API calls

## Cost Summary

- **Twitter API**: $0.00/month (RapidAPI Free: 500 calls)
- **LLM Processing**: $0.00/month (MiMo-V2-Flash free tier)
- **VPS**: ~$5-10/month (4GB RAM, 20GB storage)
- **Total**: ~$5-10/month (VPS only)

## Support

For issues:
1. Check container logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose exec nba-collector env`
3. Test API connectivity: Use test scripts in `/nba-collector/`

## Next Steps

1. Set up N8N workflows for automated collection
2. Configure time-based triggers (game times, market hours)
3. Set up monitoring and alerts
4. Implement backup automation
