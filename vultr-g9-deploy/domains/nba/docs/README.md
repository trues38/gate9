# G9 NBA Collector

Free NBA/Economy data collection system using Twitter241 API (RapidAPI Free tier).

## Quick Start

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export RAPIDAPI_KEY="your_rapidapi_key_here"

# Test Twitter API adapter
python3 test_real_api.py

# Test full pipeline
python3 test_full_pipeline.py
```

### Deploy to VPS

```bash
cd ..
./deploy_vps_nba.sh <YOUR_VPS_IP>
```

## System Overview

```
Twitter241 API  →  SQLite Storage  →  LLM Processing  →  Neo4j Graph
(500 calls/mo)     (Deduplication)    (Free MiMo-V2)     (Relationships)
```

## Features

- ✅ **Free Twitter API** - 500 calls/month via RapidAPI
- ✅ **Smart Caching** - User ID caching saves 50% of API calls
- ✅ **Raw Storage** - SQLite for reprocessing capability
- ✅ **LLM Processing** - Free MiMo-V2-Flash via OpenRouter
- ✅ **Budget Tracking** - Never exceed API quota
- ✅ **Time-Based Collection** - Only collect when needed
- ✅ **Deduplication** - Never process same tweet twice

## Budget Allocation (500 calls/month)

- NBA: 250 calls (4 per game × 60 games)
- Economy: 200 calls (5 sessions/day × 30 days)
- Buffer: 50 calls

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/budget/status` | GET | API budget usage |
| `/storage/stats` | GET | Storage statistics |
| `/collect/nba` | POST | Collect NBA tweets |
| `/collect/economy` | POST | Collect economy tweets |
| `/process/llm` | POST | Process with LLM |
| `/status` | GET | Full system status |

## Architecture

### Components

1. **Twitter API Adapter** (`sources/twttr_free_adapter.py`)
   - Twitter241 API integration
   - User ID caching
   - Budget tracking
   - Batch fetching

2. **Raw Storage** (`storage/raw_storage.py`)
   - SQLite database
   - Deduplication
   - Processing status tracking
   - API call logging

3. **LLM Processor** (`processing/llm_processor.py`)
   - Event classification (INJURY, LINEUP, REFEREE)
   - Entity extraction (Player, Team, etc.)
   - Importance scoring
   - MiMo-V2-Flash integration

4. **Scheduler** (`scheduling/time_based_scheduler.py`)
   - NBA: Event-based (before games)
   - Economy: Session-based (market hours)
   - Budget-aware

5. **Pipeline** (`main_pipeline.py`)
   - Orchestrates flow
   - Error handling
   - Status reporting

6. **REST API** (`app_api.py`)
   - Flask endpoints
   - JSON responses
   - Health checks

## Environment Variables

```bash
# Required
RAPIDAPI_KEY=your_rapidapi_key

# Optional (uses mock mode if not set)
OPENROUTER_API_KEY=your_openrouter_key

# Neo4j (for Docker deployment)
NEO4J_URI=bolt://neo4j-nba:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

## Testing

```bash
# Test API adapter
python3 test_real_api.py

# Test storage
python3 -c "
from storage.raw_storage import RawTweetStorage
storage = RawTweetStorage('data/test.db')
print(storage.get_stats())
"

# Test full pipeline
python3 test_full_pipeline.py
```

## Docker

```bash
# Build image
docker build -t g9-nba-collector .

# Run container
docker run -d \
  -p 8001:8001 \
  -e RAPIDAPI_KEY=your_key \
  --name nba-collector \
  g9-nba-collector

# Check logs
docker logs -f nba-collector
```

## Files

- `sources/twttr_free_adapter.py` - Twitter241 API adapter
- `storage/raw_storage.py` - SQLite raw storage
- `processing/llm_processor.py` - LLM event extraction
- `scheduling/time_based_scheduler.py` - Time-based scheduler
- `main_pipeline.py` - Pipeline orchestrator
- `app_api.py` - Flask REST API
- `Dockerfile` - Docker image definition
- `requirements.txt` - Python dependencies
- `test_*.py` - Test scripts

## Documentation

- `IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `../VPS_DEPLOYMENT_GUIDE_NBA.md` - Deployment guide
- `../NBA_COLLECTOR_QUICKSTART.md` - Quick reference

## Cost

- Twitter API: $0/month (RapidAPI Free)
- LLM Processing: $0/month (MiMo-V2-Flash Free)
- **Total: $0/month** (excluding VPS hosting)

## License

Internal G9 project

## Author

Built for G9 Sports Intelligence Platform
