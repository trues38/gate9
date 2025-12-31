"""
G9 Sports Intelligence Platform
FastAPI Server
"""

import os
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from orchestrator import G9Orchestrator


# ============================================
# Pydantic Models
# ============================================

class EventResponse(BaseModel):
    sport: str
    event_type: str
    player: Optional[str]
    team: Optional[str]
    status: Optional[str]
    source: str
    source_tier: int
    timestamp: datetime
    confidence: float


class PostGameRequest(BaseModel):
    game_id: str
    teams: List[str]


class PostGameResponse(BaseModel):
    game_id: str
    teams: List[str]
    overall_sentiment: Optional[str]
    players_evaluated: int
    key_insights: List[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    enabled_sports: List[str]


# ============================================
# App Initialization
# ============================================

# Global orchestrators cache
orchestrators = {}


def get_orchestrator(sport: str) -> G9Orchestrator:
    """Get or create orchestrator for sport"""
    if sport not in orchestrators:
        orchestrators[sport] = G9Orchestrator(sport)
    return orchestrators[sport]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    enabled_sports = os.getenv('G9_ENABLED_SPORTS', 'NBA').split(',')
    for sport in enabled_sports:
        sport = sport.strip().lower()
        try:
            orchestrators[sport] = G9Orchestrator(sport)
            print(f"[Startup] Initialized {sport.upper()} orchestrator")
        except Exception as e:
            print(f"[Startup] Failed to initialize {sport}: {e}")

    yield

    # Shutdown
    for sport, orch in orchestrators.items():
        if orch._neo4j_driver:
            orch._neo4j_driver.close()
    print("[Shutdown] Cleaned up resources")


app = FastAPI(
    title="G9 Sports Intelligence API",
    description="Domain Experts + Fast X + Deep Reddit + Remembering Graph",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        enabled_sports=list(orchestrators.keys())
    )


# ============================================
# Layer 1: Real-time Events
# ============================================

@app.get("/api/{sport}/events", response_model=List[EventResponse])
async def get_realtime_events(
    sport: str,
    event_type: Optional[str] = None
):
    """
    Get real-time events for a sport

    - **sport**: Sport code (nba, nfl, mlb)
    - **event_type**: Filter by type (injury, lineup, trade)
    """
    try:
        orch = get_orchestrator(sport.lower())
        event_types = [event_type] if event_type else ["injury", "lineup"]
        events = await orch.search_realtime_events(event_types)

        return [
            EventResponse(
                sport=e.sport,
                event_type=e.event_type.value,
                player=e.player,
                team=e.team,
                status=e.status,
                source=e.source,
                source_tier=e.source_tier,
                timestamp=e.timestamp,
                confidence=e.confidence
            )
            for e in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/{sport}/events/{team}")
async def get_team_events(sport: str, team: str):
    """Get real-time events for a specific team"""
    try:
        orch = get_orchestrator(sport.lower())
        events = await orch.search_realtime_events()

        team_events = [
            e for e in events
            if e.team and e.team.upper() == team.upper()
        ]

        return [
            EventResponse(
                sport=e.sport,
                event_type=e.event_type.value,
                player=e.player,
                team=e.team,
                status=e.status,
                source=e.source,
                source_tier=e.source_tier,
                timestamp=e.timestamp,
                confidence=e.confidence
            )
            for e in team_events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Layer 2: Post-Game Analysis
# ============================================

@app.post("/api/{sport}/postgame", response_model=PostGameResponse)
async def trigger_postgame_analysis(
    sport: str,
    request: PostGameRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger post-game analysis collection

    - Collects Reddit Post-Game Thread
    - Analyzes with LLM
    - Stores in Neo4j Graph
    """
    try:
        orch = get_orchestrator(sport.lower())

        # Run analysis
        results = await orch.run_full_postgame_pipeline(
            request.game_id,
            request.teams
        )

        if results["reddit_analysis"]:
            return PostGameResponse(
                game_id=request.game_id,
                teams=request.teams,
                overall_sentiment=results["reddit_analysis"]["overall_sentiment"],
                players_evaluated=results["stored_evaluations"],
                key_insights=results["reddit_analysis"]["key_insights"]
            )
        else:
            return PostGameResponse(
                game_id=request.game_id,
                teams=request.teams,
                overall_sentiment=None,
                players_evaluated=0,
                key_insights=[]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Layer 3: Graph Queries
# ============================================

@app.get("/api/{sport}/player/{player_name}/context")
async def get_player_context(sport: str, player_name: str):
    """
    Get full context for a player from the graph

    Returns recent alerts, evaluations, and cross-validated insights
    """
    try:
        orch = get_orchestrator(sport.lower())
        context = orch.get_player_context(player_name)

        if not context:
            raise HTTPException(status_code=404, detail=f"Player {player_name} not found")

        return context

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/{sport}/pregame/{game_id}")
async def get_pregame_context(
    sport: str,
    game_id: str,
    teams: str  # comma-separated
):
    """
    Get complete pre-game context

    Combines:
    - Recent real-time events (injuries, lineup changes)
    - Graph memory (historical patterns)
    - Expert data validations
    """
    try:
        orch = get_orchestrator(sport.lower())
        team_list = [t.strip() for t in teams.split(',')]

        context = await orch.get_pregame_context(game_id, team_list)

        return {
            "game_id": context.game_id,
            "teams": context.teams,
            "realtime_events": [
                {
                    "type": e.event_type.value,
                    "player": e.player,
                    "team": e.team,
                    "status": e.status,
                    "source_tier": e.source_tier
                }
                for e in context.realtime_events
            ],
            "graph_context": context.graph_context
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Layer 0: Data Sync
# ============================================

@app.post("/api/{sport}/sync")
async def sync_expert_data(
    sport: str,
    background_tasks: BackgroundTasks,
    force: bool = False
):
    """
    Trigger expert data sync from Kaggle

    Runs in background
    """
    try:
        orch = get_orchestrator(sport.lower())

        # Run in background
        background_tasks.add_task(orch.sync_expert_data, force)

        return {
            "status": "started",
            "message": f"Syncing expert data for {sport.upper()}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
