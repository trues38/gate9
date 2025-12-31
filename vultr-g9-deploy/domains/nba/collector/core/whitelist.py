"""
Whitelist Manager - Account-based filtering with state awareness

Tiers:
- S: Top insiders (Shams, Woj, Underdog) - Always priority
- A: Lineup/Injury bots (FantasyLabs, NBALineups)
- B: Referees (OfficialNBARefs)
- C: Beat writers (analysis, not realtime)
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum
from .game_state import GameState
import logging

logger = logging.getLogger(__name__)


class AccountType(Enum):
    INSIDER = "insider"
    INJURY_BOT = "injury_bot"
    LINEUP_BOT = "lineup_bot"
    REFEREE = "referee"
    TEAM_OFFICIAL = "team_official"
    BEAT_WRITER = "beat_writer"


class Tier(Enum):
    S = 1  # Alarm-level priority
    A = 2  # High priority
    B = 3  # Medium priority
    C = 4  # Low priority (analysis only)


@dataclass
class WhitelistAccount:
    """Single whitelisted account"""
    username: str
    account_type: AccountType
    tier: Tier
    priority: int  # Lower = higher priority
    allowed_states: Set[GameState]
    credibility: float = 1.0  # 0.0 - 1.0
    team: Optional[str] = None  # For team official accounts

    def is_allowed_in_state(self, state: GameState) -> bool:
        """Check if account should be queried in given state"""
        return state in self.allowed_states


# Pre-configured whitelist
DEFAULT_WHITELIST = [
    # === TIER S: Alarm-level (Always monitor) ===
    WhitelistAccount(
        username="ShamsCharania",
        account_type=AccountType.INSIDER,
        tier=Tier.S,
        priority=1,
        allowed_states={GameState.PRE_GAME_ACTIVE, GameState.IN_GAME_ACTIVE},
        credibility=1.0
    ),
    WhitelistAccount(
        username="wojespn",
        account_type=AccountType.INSIDER,
        tier=Tier.S,
        priority=2,
        allowed_states={GameState.PRE_GAME_ACTIVE, GameState.IN_GAME_ACTIVE},
        credibility=1.0
    ),
    WhitelistAccount(
        username="UnderdogNBA",
        account_type=AccountType.LINEUP_BOT,
        tier=Tier.S,
        priority=3,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.95
    ),

    # === TIER A: Lineup/Injury bots ===
    WhitelistAccount(
        username="FantasyLabsNBA",
        account_type=AccountType.INJURY_BOT,
        tier=Tier.A,
        priority=10,
        allowed_states={GameState.PRE_GAME_ACTIVE, GameState.IN_GAME_ACTIVE},
        credibility=0.9
    ),
    WhitelistAccount(
        username="Rotoworld_BK",
        account_type=AccountType.INJURY_BOT,
        tier=Tier.A,
        priority=11,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.85
    ),
    WhitelistAccount(
        username="NBAFantasy",
        account_type=AccountType.LINEUP_BOT,
        tier=Tier.A,
        priority=12,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.85
    ),

    # === TIER B: Referees ===
    WhitelistAccount(
        username="OfficialNBARefs",
        account_type=AccountType.REFEREE,
        tier=Tier.B,
        priority=20,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=1.0
    ),
    WhitelistAccount(
        username="NBARefStats",
        account_type=AccountType.REFEREE,
        tier=Tier.B,
        priority=21,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.9
    ),

    # === TIER S: Additional Top Insiders ===
    WhitelistAccount(
        username="ChrisBHaynes",
        account_type=AccountType.INSIDER,
        tier=Tier.S,
        priority=4,
        allowed_states={GameState.PRE_GAME_ACTIVE, GameState.IN_GAME_ACTIVE},
        credibility=0.95
    ),

    # === TIER A: Additional Injury/Lineup Bots ===
    WhitelistAccount(
        username="NBAInjuryR3p0rt",
        account_type=AccountType.INJURY_BOT,
        tier=Tier.A,
        priority=13,
        allowed_states={GameState.PRE_GAME_ACTIVE, GameState.IN_GAME_ACTIVE},
        credibility=0.85
    ),
    WhitelistAccount(
        username="FantasyLabsDFS",
        account_type=AccountType.LINEUP_BOT,
        tier=Tier.A,
        priority=14,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.85
    ),
    WhitelistAccount(
        username="RotoGrinders",
        account_type=AccountType.LINEUP_BOT,
        tier=Tier.A,
        priority=15,
        allowed_states={GameState.PRE_GAME_ACTIVE},
        credibility=0.8
    ),
]

# TIER C (Beat Writers) - DISABLED for efficiency
# Only injury/lineup/referee data matters for betting
# Beat writer analysis is post-hoc and doesn't affect lines
TIER_C_DISABLED = [
    # "TimBontemps", "KevinOConnorNBA", "ZachLowe_NBA",
    # "RamonaShelburne", "WindhorstESPN", "ChrisMannixYS"
]

# Team official accounts (dynamically filtered by today's games)
NBA_TEAM_ACCOUNTS = {
    "LAL": "Lakers",
    "GSW": "warriors",
    "BOS": "celtics",
    "MIA": "MiamiHEAT",
    "NYK": "nyknicks",
    "BKN": "BrooklynNets",
    "PHI": "sixers",
    "MIL": "Bucks",
    "LAC": "LAClippers",
    "DEN": "nuggets",
    "PHX": "Suns",
    "DAL": "dalaborems",
    "MEM": "memgrizz",
    "NOP": "PelicansNBA",
    "OKC": "oaboremcthunder",
    "MIN": "Timberwolves",
    "POR": "trailblazers",
    "SAC": "SacramentoKings",
    "SAS": "spurs",
    "HOU": "HoustonRockets",
    "UTA": "utahjazz",
    "ATL": "ATLHawks",
    "CHA": "hornets",
    "CHI": "chicagobulls",
    "CLE": "cavs",
    "DET": "DetroitPistons",
    "IND": "Pacers",
    "ORL": "OrlandoMagic",
    "TOR": "Raptors",
    "WAS": "WashWizards",
}


class WhitelistManager:
    """Manages whitelist accounts with state-based filtering"""

    def __init__(self, accounts: List[WhitelistAccount] = None):
        self.accounts = accounts or DEFAULT_WHITELIST.copy()
        self._index_by_username = {a.username.lower(): a for a in self.accounts}

    def get_accounts_for_state(self, state: GameState) -> List[WhitelistAccount]:
        """Get accounts that should be queried in given state"""
        if state in [GameState.WAITING, GameState.DEAD, GameState.LOCKED]:
            return []

        accounts = [a for a in self.accounts if a.is_allowed_in_state(state)]
        return sorted(accounts, key=lambda a: a.priority)

    def get_accounts_by_tier(self, tier: Tier) -> List[WhitelistAccount]:
        """Get accounts by tier"""
        return [a for a in self.accounts if a.tier == tier]

    def get_account(self, username: str) -> Optional[WhitelistAccount]:
        """Get account by username"""
        return self._index_by_username.get(username.lower())

    def get_credibility(self, username: str) -> float:
        """Get credibility score for account"""
        account = self.get_account(username)
        return account.credibility if account else 0.3  # Default low credibility

    def add_team_accounts(self, team_codes: List[str]):
        """Dynamically add team official accounts for today's games"""
        for code in team_codes:
            if code in NBA_TEAM_ACCOUNTS:
                username = NBA_TEAM_ACCOUNTS[code]
                if username.lower() not in self._index_by_username:
                    account = WhitelistAccount(
                        username=username,
                        account_type=AccountType.TEAM_OFFICIAL,
                        tier=Tier.A,
                        priority=15,
                        allowed_states={GameState.PRE_GAME_ACTIVE},
                        credibility=0.9,
                        team=code
                    )
                    self.accounts.append(account)
                    self._index_by_username[username.lower()] = account
                    logger.info(f"Added team account: @{username} ({code})")

    def get_stats(self) -> dict:
        """Get whitelist statistics"""
        return {
            "total": len(self.accounts),
            "by_tier": {t.name: len(self.get_accounts_by_tier(t)) for t in Tier},
            "by_type": {t.value: len([a for a in self.accounts if a.account_type == t]) for t in AccountType}
        }


# Keywords for filtering (STRICT - only actionable betting signals)
KEYWORDS = {
    "PRE_GAME": {
        # CRITICAL: Player availability (affects lines immediately)
        "injury": [
            "out", "ruled out", "will not play", "sidelined",
            "out tonight", "out today", "won't play", "inactive"
        ],
        "questionable": [
            "questionable", "doubtful", "probable", "gtd", "game-time decision",
            "game time decision", "gametime"
        ],
        # CRITICAL: Starting lineups (sharp money indicator)
        "lineup": [
            "will start", "starting", "starting lineup", "starting five",
            "starts tonight", "gets the start", "in the starting lineup"
        ],
        # CRITICAL: Referee assignments (total/foul tendencies)
        "referee": [
            "crew chief", "referee", "officiating crew", "ref assignment",
            "tonight's officials", "referees for"
        ],
        # IMPORTANT: Playing restrictions
        "restriction": [
            "minutes restriction", "minute limit", "load management",
            "rest", "dnp-rest", "maintenance day"
        ]
    },
    "IN_GAME": {
        # CRITICAL: In-game injuries (live betting impact)
        "injury": [
            "injury", "injured", "left the game", "to the locker room",
            "headed to locker", "limping", "grabbing", "ruled out"
        ],
        # IMPORTANT: Ejections (live betting shift)
        "ejection": [
            "ejected", "ejection", "thrown out", "tossed",
            "technical foul", "flagrant"
        ],
    }
}

# Keywords to EXCLUDE (noise reduction)
EXCLUDE_KEYWORDS = [
    "last night", "yesterday", "last week", "previously",
    "history", "career", "season", "year ago",
    "trade", "rumor", "report says", "could be", "might",
    "analysis", "breakdown", "film", "highlights"
]


def keyword_match(text: str, state: GameState) -> Optional[str]:
    """
    Check if text matches any keywords for the state

    STRICT filtering: Only actionable betting signals
    - Injury status (OUT/IN/Questionable)
    - Lineup confirmations
    - Referee assignments

    Excludes:
    - Historical analysis
    - Trade rumors
    - Post-game commentary
    """
    text_lower = text.lower()

    # STEP 1: Exclude noise
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in text_lower:
            return None  # Skip historical/analysis content

    # STEP 2: Match actionable keywords
    if state == GameState.PRE_GAME_ACTIVE:
        keywords = KEYWORDS["PRE_GAME"]
    elif state == GameState.IN_GAME_ACTIVE:
        keywords = KEYWORDS["IN_GAME"]
    else:
        return None

    for category, words in keywords.items():
        for word in words:
            if word in text_lower:
                return category

    return None
