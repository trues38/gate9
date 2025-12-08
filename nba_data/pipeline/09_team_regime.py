import json
import os
import numpy as np

class TeamRegimeEngine:
    """
    Phase 2: Team Regime Engine.
    Aggregates Player Regimes into Team-Level Insights.
    """
    
    DATA_DIR = "nba_data"
    REGIME_FILE = os.path.join(DATA_DIR, "regimes", "regimes_with_dna.json")
    PLAYERS_META = os.path.join(DATA_DIR, "players", "top_250_active.json")
    OUTPUT_FILE = os.path.join(DATA_DIR, "regimes", "team_regimes.json")
    
    # Team Names Map (ID -> Name) - Simplified Stub or Loaded
    TEAM_NAMES = {
        1: "Atlanta Hawks", 2: "Boston Celtics", 3: "Brooklyn Nets", 4: "Charlotte Hornets",
        5: "Chicago Bulls", 6: "Cleveland Cavaliers", 7: "Dallas Mavericks", 8: "Denver Nuggets",
        9: "Detroit Pistons", 10: "Golden State Warriors", 11: "Houston Rockets", 12: "Indiana Pacers",
        13: "LA Clippers", 14: "Los Angeles Lakers", 15: "Memphis Grizzlies", 16: "Miami Heat",
        17: "Milwaukee Bucks", 18: "Minnesota Timberwolves", 19: "New Orleans Pelicans", 20: "New York Knicks",
        21: "Oklahoma City Thunder", 22: "Orlando Magic", 23: "Philadelphia 76ers", 24: "Phoenix Suns",
        25: "Portland Trail Blazers", 26: "Sacramento Kings", 27: "San Antonio Spurs", 28: "Toronto Raptors",
        29: "Utah Jazz", 30: "Washington Wizards"
    }

    def load_data(self):
        with open(self.REGIME_FILE, 'r') as f:
            players = json.load(f)
        with open(self.PLAYERS_META, 'r') as f:
            meta = json.load(f)
            
        # Map Player ID -> Team ID
        pid_to_tid = {p['id']: p['team_id'] for p in meta}
        
        # Group Players by Team
        teams = {}
        for p in players:
            pid = p['id']
            tid = pid_to_tid.get(pid)
            if not tid: continue
            
            if tid not in teams: teams[tid] = []
            teams[tid].append(p)
            
        return teams

    def calculate_team_metrics(self, players):
        """
        Aggregates individual player metrics into a team profile.
        """
        if not players: return None
        
        # Sort by Momentum Score (Identify Stars vs Bench)
        # Assuming 'regime' key exists
        players.sort(key=lambda x: x['regime']['momentum_score'], reverse=True)
        
        # 1. Momentum Sum (Weighted)
        # Top 3 players get 1.5x weight
        total_momentum = 0
        weights = []
        scores = []
        
        for i, p in enumerate(players):
            score = p['regime']['momentum_score']
            w = 1.5 if i < 3 else 1.0
            total_momentum += score * w
            weights.append(w)
            scores.append(score)
            
        avg_momentum = total_momentum / sum(weights)
        
        # 2. Variance / Volatility
        # Standard deviation of player momentums (High std = disjointed team?)
        # Also check for "Volatile" tags in context
        tags = []
        for p in players:
            tags.extend(p['regime']['narrative_context'])
            
        volatility_score = 0
        if "Volatile" in tags: volatility_score += 0.5
        if "HighVariance" in tags: volatility_score += 0.8
        
        # Add std dev component
        score_std = np.std(scores) if len(scores) > 1 else 0
        volatility_score += score_std
        
        return {
            "avg_momentum": round(avg_momentum, 2),
            "volatility": round(volatility_score, 2),
            "dominant_tags": list(set(tags))[:5] # Top 5 unique tags
        }

    def determine_label(self, metrics):
        mom = metrics['avg_momentum']
        vol = metrics['volatility']
        
        # Labels
        if mom > 1.0: base = "Juggernaut"
        elif mom > 0.5: base = "Surging"
        elif mom > 0.0: base = "Stable"
        elif mom > -0.5: base = "Shaky"
        else: base = "Collapsing"
        
        suffix = ""
        if vol > 0.8: suffix = " (High Variance)"
        elif vol < 0.2: suffix = " (Systematic)"
        
        return f"{base}{suffix}"

    def run(self):
        print("🏙️ Building Team Regimes...")
        teams_data = self.load_data()
        
        final_teams = []
        
        for tid, players in teams_data.items():
            metrics = self.calculate_team_metrics(players)
            if not metrics: continue
            
            label = self.determine_label(metrics)
            
            team_obj = {
                "team_id": tid,
                "team_name": self.TEAM_NAMES.get(tid, f"Team {tid}"),
                "regime_label": label,
                "momentum": metrics['avg_momentum'],
                "volatility": metrics['volatility'],
                "key_narratives": metrics['dominant_tags'],
                "roster_size": len(players)
                # Could add "Coach Style" via inference later
            }
            final_teams.append(team_obj)
            
        # Save
        with open(self.OUTPUT_FILE, 'w') as f:
            json.dump(final_teams, f, indent=2)
            
        print(f"✅ Generated regimes for {len(final_teams)} teams.")
        print(f"📄 Saved to {self.OUTPUT_FILE}")
        
        # Sample
        if final_teams:
            print("\nSAMPLE TEAM:")
            print(final_teams[0])

if __name__ == "__main__":
    engine = TeamRegimeEngine()
    engine.run()
