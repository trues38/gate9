
import pandas as pd
import numpy as np

class TrapEngine:
    def __init__(self):
        # Configuration for Scoring
        self.weights = {
            "momentum": 2.0,
            "confidence": 1.5,
            "memory": 1.2,
            "variance": 1.0
        }
        
    def detect_momentum_trap(self, row):
        """
        Layer 1: Momentum Trap
        Condition: STRONG_UP Flow (Overheated)
        Ideally: Recent Gap > 6, Long Gap < 2 (Proxy: Just STRONG_UP for now)
        """
        if row.get('flow_state') == 'STRONG_UP':
            return 1
        return 0
        
    def detect_confidence_trap(self, row):
        """
        Layer 2: Confidence Trap
        Condition: Fav Confidence HIGH (Implied via Fav Pct > 65% but not Extreme)
        AND Public Consensus (Proxy: Fav Pct as market line proxy)
        """
        # User Def: Edge [70, 80) + High Confidence
        edge = row.get('edge_score', 0)
        fav_pct = row.get('fav_pct', 0)
        
        # High Confidence Definition: 65% - 75% Prob?
        is_high_conf = (0.65 <= fav_pct < 0.75)
        is_trap_edge = (70 <= edge < 80)
        
        if is_high_conf and is_trap_edge:
            return 1
        return 0
        
    def calculate_trap_score(self, row):
        """
        Compute Weighted Score
        """
        score = 0.0
        
        # Layer 1
        if self.detect_momentum_trap(row):
            score += self.weights['momentum']
            
        # Layer 2
        if self.detect_confidence_trap(row):
            score += self.weights['confidence']
            
        # Layer 3/4 (Placeholder for future data engineering)
        
        return score

    def classify_trap(self, score):
        if score >= 3.5:
            return "HARD_TRAP"
        elif score >= 2.5:
            return "SOFT_TRAP"
        else:
            return "PASS"

    def run_batch(self, df):
        """
        Apply to DataFrame
        """
        # 1. Universe Filter: 65 <= Edge < 80 (User Spec)
        # Actually user said 65 <= Edge < 80 AND Fav_Confidence HIGH
        # But let's score everything first, then filter? Or strict filtering?
        # User: "Universe = 65 <= Edge < 80"
        
        mask_universe = (df['edge_score'] >= 65) & (df['edge_score'] < 80)
        target_df = df[mask_universe].copy()
        
        if target_df.empty:
            return target_df
            
        # Apply Logic
        target_df['momentum_flag'] = target_df.apply(self.detect_momentum_trap, axis=1)
        target_df['confidence_flag'] = target_df.apply(self.detect_confidence_trap, axis=1)
        
        target_df['trap_score'] = target_df.apply(self.calculate_trap_score, axis=1)
        target_df['trap_level'] = target_df['trap_score'].apply(self.classify_trap)
        
        return target_df

# Standalone execution for testing
if __name__ == "__main__":
    pass
