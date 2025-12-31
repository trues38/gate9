#!/usr/bin/env python3
"""
Fix for NBA Collection Window Issue

Current problem:
- Collection window: T-1h (before first game) to T-0 (when last game starts)
- Misses all live-game and post-game tweets

New strategy:
- Collection window: T-1h (before first game) to T+4h (after last game starts)
- This covers: pre-game, during game (~2.5h), and post-game analysis
"""

PATCH = '''
def should_collect_nba(self, game_times: List[datetime]) -> bool:
    """
    Determine if NBA collection should happen now

    Collection strategy:
    - Start: 1 hour before FIRST game
    - End: 4 hours after LAST game starts (covers full game + post-game)
    - Frequency: Every 30 minutes (via N8N cron)

    This ensures continuous collection during:
    - Pre-game warmup (T-1h to T-0)
    - Live game (T-0 to T+2.5h)
    - Post-game analysis (T+2.5h to T+4h)

    Args:
        game_times: List of scheduled game times (datetime objects)

    Returns:
        True if we're in a collection window
    """
    if self.nba_used >= self.nba_budget:
        logger.warning("NBA budget exceeded")
        return False

    if not game_times:
        logger.debug("No games scheduled - skip NBA collection")
        return False

    now = datetime.now()

    # Find earliest and latest games
    first_game = min(game_times)
    last_game = max(game_times)

    # Collection window: T-1h (first game) to T+4h (last game)
    collection_start = first_game - timedelta(hours=1)
    collection_end = last_game + timedelta(hours=4)  # CHANGED: Added +4h for live + post-game

    if collection_start <= now <= collection_end:
        time_to_first = (first_game - now).total_seconds() / 60
        time_to_last = (last_game - now).total_seconds() / 60
        time_since_last = (now - last_game).total_seconds() / 60

        if now < first_game:
            logger.info(f"NBA collection active - PRE-GAME (First game in {time_to_first:.0f}m)")
        elif now < last_game:
            logger.info(f"NBA collection active - LIVE GAMES (Last game in {time_to_last:.0f}m)")
        else:
            logger.info(f"NBA collection active - POST-GAME ({time_since_last:.0f}m since last game)")

        return True

    if now < collection_start:
        logger.debug(f"Not in collection window (starts in {(collection_start - now).total_seconds() / 60:.0f}m)")
    else:
        logger.debug(f"Not in collection window (ended {(now - collection_end).total_seconds() / 60:.0f}m ago)")

    return False
'''

print("=" * 70)
print("NBA COLLECTION WINDOW FIX")
print("=" * 70)
print()
print("Problem:")
print("  - Current window: T-1h to T-0 (before first game to when last game starts)")
print("  - Misses all live and post-game tweets")
print("  - Result: Only 2 tweets collected in past 48 hours")
print()
print("Solution:")
print("  - New window: T-1h to T+4h (before first game to 4h after last game starts)")
print("  - Covers: Pre-game + Live (2.5h) + Post-game (1.5h)")
print("  - Will collect during entire game period")
print()
print("To apply this fix on VPS:")
print("  1. SSH to VPS: ssh root@141.164.35.214")
print("  2. Edit file: /opt/g9/nba-collector/scheduling/time_based_scheduler.py")
print("  3. Find the should_collect_nba method")
print("  4. Change line: collection_end = last_game")
print("  5. To: collection_end = last_game + timedelta(hours=4)")
print("  6. Restart container: docker restart g9-nba-collector")
print()
print("=" * 70)
