#!/usr/bin/env python3
"""
Graph RAG Query Templates for Soccer Betting Analysis

These Cypher queries extract context from Neo4j to feed into AI Council:
- Recent form (IMPROVING/DECLINING)
- Head-to-head history
- xG trends and regression potential
- Referee bias analysis
- Tactical matchups
"""

from neo4j import GraphDatabase
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SoccerGraphRAG:
    """Graph RAG context extraction for soccer matches"""

    def __init__(self, uri="bolt://localhost:7689", user="neo4j", password="soccer_g9_2025"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_recent_form(self, team_name: str, num_matches: int = 5) -> Dict[str, Any]:
        """
        Extract recent form for a team
        Returns: xG avg, win rate, trend (IMPROVING/DECLINING)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Team)-[rel:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
                WHERE t.name =~ $team_pattern AND m.home_xG IS NOT NULL
                WITH t, m, rel ORDER BY m.date DESC LIMIT $num

                WITH t,
                     COLLECT({
                         date: m.date,
                         xG: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.home_xG ELSE m.away_xG END,
                         xGA: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.away_xG ELSE m.home_xG END,
                         goals: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.home_score ELSE m.away_score END,
                         conceded: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.away_score ELSE m.home_score END,
                         result: m.result,
                         was_home: type(rel) = 'PLAYED_HOME'
                     }) as matches

                // Calculate recent 5 vs previous 5
                WITH t, matches,
                     matches[0..5] as recent,
                     matches[5..10] as previous

                RETURN {
                    team: t.name,
                    recent_matches: recent,
                    recent_avg_xG: reduce(s=0.0, m IN recent | s + m.xG) / size(recent),
                    recent_avg_xGA: reduce(s=0.0, m IN recent | s + m.xGA) / size(recent),
                    recent_goals: reduce(s=0, m IN recent | s + m.goals) / size(recent),
                    previous_avg_xG: reduce(s=0.0, m IN previous | s + m.xG) / CASE WHEN size(previous) > 0 THEN size(previous) ELSE 1 END,
                    win_rate: reduce(s=0, m IN recent |
                        s + CASE
                            WHEN m.result = 'HOME_WIN' AND m.was_home THEN 1
                            WHEN m.result = 'AWAY_WIN' AND NOT m.was_home THEN 1
                            ELSE 0
                        END
                    ) * 100.0 / size(recent)
                } as form
            """, team_pattern=f".*{team_name}.*", num=num_matches * 2)

            record = result.single()
            if not record:
                return {}

            form = dict(record['form'])

            # Determine trend
            if form['recent_avg_xG'] > form['previous_avg_xG'] * 1.1:
                form['trend'] = 'IMPROVING'
            elif form['recent_avg_xG'] < form['previous_avg_xG'] * 0.9:
                form['trend'] = 'DECLINING'
            else:
                form['trend'] = 'STABLE'

            return form

    def get_head_to_head(self, home_team: str, away_team: str, num_matches: int = 5) -> List[Dict]:
        """
        Get head-to-head history between two teams
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (h:Team)-[:PLAYED_HOME]->(m:Match)<-[:PLAYED_AWAY]-(a:Team)
                WHERE h.name =~ $home_pattern AND a.name =~ $away_pattern
                WITH m ORDER BY m.date DESC LIMIT $num
                RETURN m.date as date,
                       m.home_score as home_score,
                       m.away_score as away_score,
                       m.home_xG as home_xG,
                       m.away_xG as away_xG,
                       m.result as result
                ORDER BY m.date DESC
            """, home_pattern=f".*{home_team}.*", away_pattern=f".*{away_team}.*", num=num_matches)

            return [dict(r) for r in result]

    def get_xG_regression_potential(self, team_name: str, num_matches: int = 15) -> Dict[str, Any]:
        """
        Analyze xG vs actual goals for regression potential

        Key metric: xG_diff (negative = unlucky, positive = overperforming)
        Large negative diff = high regression potential (buy signal)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Team)-[rel:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
                WHERE t.name =~ $team_pattern AND m.home_xG IS NOT NULL
                WITH t, m, rel ORDER BY m.date DESC LIMIT $num

                WITH t,
                     COLLECT({
                         xG: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.home_xG ELSE m.away_xG END,
                         goals: CASE WHEN type(rel) = 'PLAYED_HOME' THEN m.home_score ELSE m.away_score END
                     }) as matches

                WITH t,
                     reduce(s=0.0, m IN matches | s + m.xG) as total_xG,
                     reduce(s=0, m IN matches | s + m.goals) as total_goals

                RETURN {
                    team: t.name,
                    total_xG: total_xG,
                    total_goals: total_goals,
                    xG_diff: total_goals - total_xG,
                    regression_potential: CASE
                        WHEN total_goals - total_xG < -5 THEN 'HIGH'
                        WHEN total_goals - total_xG < -2 THEN 'MEDIUM'
                        WHEN total_goals - total_xG > 5 THEN 'NEGATIVE_HIGH'
                        WHEN total_goals - total_xG > 2 THEN 'NEGATIVE_MEDIUM'
                        ELSE 'LOW'
                    END
                } as regression
            """, team_pattern=f".*{team_name}.*", num=num_matches)

            record = result.single()
            return dict(record['regression']) if record else {}

    def get_referee_bias(self, referee_name: str, team_name: str = None) -> Dict[str, Any]:
        """
        Analyze referee bias (home advantage, cards, etc.)
        """
        with self.driver.session() as session:
            if team_name:
                # Team-specific referee record
                result = session.run("""
                    MATCH (r:Referee)-[:OFFICIATED]->(m:Match)
                    WHERE r.name =~ $ref_pattern
                    MATCH (t:Team)-[:PLAYED_HOME|PLAYED_AWAY]->(m)
                    WHERE t.name =~ $team_pattern

                    WITH t, m,
                         CASE WHEN exists((t)-[:PLAYED_HOME]->(m)) THEN 'HOME' ELSE 'AWAY' END as venue

                    RETURN {
                        team: t.name,
                        referee: r.name,
                        total_matches: count(m),
                        wins: sum(CASE
                            WHEN m.result = 'HOME_WIN' AND venue = 'HOME' THEN 1
                            WHEN m.result = 'AWAY_WIN' AND venue = 'AWAY' THEN 1
                            ELSE 0
                        END),
                        draws: sum(CASE WHEN m.result = 'DRAW' THEN 1 ELSE 0 END),
                        losses: sum(CASE
                            WHEN m.result = 'AWAY_WIN' AND venue = 'HOME' THEN 1
                            WHEN m.result = 'HOME_WIN' AND venue = 'AWAY' THEN 1
                            ELSE 0
                        END)
                    } as record
                """, ref_pattern=f".*{referee_name}.*", team_pattern=f".*{team_name}.*")
            else:
                # Overall referee bias
                result = session.run("""
                    MATCH (r:Referee)-[:OFFICIATED]->(m:Match)
                    WHERE r.name =~ $ref_pattern AND m.result IS NOT NULL

                    WITH r,
                         count(m) as total,
                         sum(CASE WHEN m.result = 'HOME_WIN' THEN 1 ELSE 0 END) as home_wins,
                         sum(CASE WHEN m.result = 'DRAW' THEN 1 ELSE 0 END) as draws

                    RETURN {
                        referee: r.name,
                        total_matches: total,
                        home_win_rate: home_wins * 100.0 / total,
                        draw_rate: draws * 100.0 / total,
                        bias: CASE
                            WHEN home_wins * 100.0 / total > 50 THEN 'HOME_FAVORING'
                            WHEN home_wins * 100.0 / total < 40 THEN 'AWAY_FAVORING'
                            ELSE 'NEUTRAL'
                        END
                    } as bias
                """, ref_pattern=f".*{referee_name}.*")

            record = result.single()
            return dict(record['record'] if team_name else record['bias']) if record else {}

    def get_tactical_matchup(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Get tactical information (manager, formation, style)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (ht:Team)<-[:MANAGES]-(hm:Manager)
                WHERE ht.name =~ $home_pattern
                OPTIONAL MATCH (hm)-[:USES]->(hf:Formation)
                OPTIONAL MATCH (hm)-[:PREFERS]->(htac:Tactic)

                MATCH (at:Team)<-[:MANAGES]-(am:Manager)
                WHERE at.name =~ $away_pattern
                OPTIONAL MATCH (am)-[:USES]->(af:Formation)
                OPTIONAL MATCH (am)-[:PREFERS]->(atac:Tactic)

                RETURN {
                    home_manager: hm.name,
                    home_formation: hf.name,
                    home_tactic: htac.name,
                    away_manager: am.name,
                    away_formation: af.name,
                    away_tactic: atac.name
                } as tactical
            """, home_pattern=f".*{home_team}.*", away_pattern=f".*{away_team}.*")

            record = result.single()
            return dict(record['tactical']) if record else {}

    def extract_full_context(self, home_team: str, away_team: str, referee_name: str = None) -> Dict[str, Any]:
        """
        Extract complete Graph RAG context for match analysis

        This is the master function that AI Council will use
        """
        context = {
            'match': {
                'home_team': home_team,
                'away_team': away_team,
                'referee': referee_name
            },
            'home_form': self.get_recent_form(home_team),
            'away_form': self.get_recent_form(away_team),
            'head_to_head': self.get_head_to_head(home_team, away_team),
            'home_regression': self.get_xG_regression_potential(home_team),
            'away_regression': self.get_xG_regression_potential(away_team),
            'tactical': self.get_tactical_matchup(home_team, away_team)
        }

        if referee_name:
            context['referee_bias'] = self.get_referee_bias(referee_name)
            context['home_referee_record'] = self.get_referee_bias(referee_name, home_team)
            context['away_referee_record'] = self.get_referee_bias(referee_name, away_team)

        return context


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    rag = SoccerGraphRAG()

    try:
        print("=== Liverpool Recent Form ===")
        form = rag.get_recent_form("Liverpool")
        print(f"Trend: {form.get('trend')}")
        print(f"Recent avg xG: {form.get('recent_avg_xG', 0):.2f}")
        print(f"Win rate: {form.get('win_rate', 0):.1f}%")

        print("\n=== Liverpool xG Regression ===")
        regression = rag.get_xG_regression_potential("Liverpool")
        print(f"xG diff: {regression.get('xG_diff', 0):.2f}")
        print(f"Potential: {regression.get('regression_potential')}")

        print("\n=== Full Match Context (Example) ===")
        context = rag.extract_full_context("Liverpool", "Arsenal")
        print(f"Home trend: {context['home_form'].get('trend')}")
        print(f"Away trend: {context['away_form'].get('trend')}")
        print(f"H2H history: {len(context['head_to_head'])} matches")

    finally:
        rag.close()
