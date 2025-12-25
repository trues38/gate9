import pandas as pd

# 🚨 THE THIRD RAIL LIST
# Features containing these strings are STRICTLY FORBIDDEN in X (Inputs)
BANNED_KEYWORDS = [
    'score', 'points', 'result', 'win', 'loss', 'margin', 
    'delta', 'headline', 'narrative', 'regime_type', # Target itself
    'boxscore', 'fg', 'ft', 'reb', 'ast', 'tov', # Post-game stats (unless '_L' rolling)
    'plus_minus', 'cover', 'pnl'
]

# ALLOWED EXCEPTIONS (Whitelist of suspicious but safe terms)
# e.g. 'previous_score' implies pre-game. But let's be strict first.
# 'points_avg' (OK), 'points_L10' (OK).
# The banned list checks SUBSTRINGS. So 'Points' bans 'Points_L10'?
# We must be careful.
# Better logic: Banned if exact match or specific suffix?
# User instruction: "Points, OpponentPoints, V" (Raw Result Columns).

# REFINED BANNED LIST (Suffixes/Prefixes)
BANNED_EXACT = [
    'Points', 'OpponentPoints', 'Score', 'OpponentScore', 
    'Result', 'Win', 'Loss', 'Margin', 'Spread_Result',
    'Cover', 'Regime_Type', 'Regime_Delta', 'Headline',
    'V', 'HomePoints', 'AwayPoints'
]

def scan_features(columns: list):
    """
    Scans a list of column names for extensive leakage risks.
    Raises ValueError if any banned features are found.
    """
    leaks = []
    
    for col in columns:
        # Check Exact Banned
        if col in BANNED_EXACT:
            leaks.append(col)
            continue
            
        # Check suspicious "Post-Game" patterns
        # e.g. "Points" without "Avg", "L10", "Sea", "Opp" etc?
        # If column is just "Points" -> Leak.
        # If "Points_L10" -> Safe.
        
        # Keyword checks
        lower_col = col.lower()
        if 'headline' in lower_col: leaks.append(col)
        if 'narrative' in lower_col: leaks.append(col)
        if 'regime_delta' in lower_col: leaks.append(col)
        if 'result' in lower_col and 'last' not in lower_col: leaks.append(col) # 'result' bad, 'result_last_10' ok? No, keep it safe.
        
    if leaks:
        error_msg = f"🚨 DATA LEAKAGE DETECTED! Found banned columns: {leaks}"
        print(error_msg)
        raise ValueError(error_msg)
    else:
        print("✅ Leakage Scan Passed. Features are clean.")
        return True
