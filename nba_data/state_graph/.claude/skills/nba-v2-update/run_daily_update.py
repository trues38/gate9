#!/usr/bin/env python3
"""
NBA v2.0 Daily Update Orchestrator

Combines all daily update tasks into one workflow
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def run_script(script_name: str, description: str) -> bool:
    """Execute a Python script and return success status"""
    script_path = Path(__file__).parent.parent.parent / script_name

    print(f"▶ {description}")
    print(f"  Script: {script_name}")
    print()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False,
            cwd=script_path.parent
        )
        print(f"  ✅ {description} - COMPLETED\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {description} - FAILED (exit code {e.returncode})\n")
        return False
    except FileNotFoundError:
        print(f"  ⚠️  Script not found: {script_path}\n")
        return False

def main():
    print_header("NBA v2.0 Daily Update Workflow")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {}

    # Step 1: Collect yesterday's games
    print_header("Step 1/4: Collect Yesterday's Games + Box Scores")
    results['games'] = run_script(
        'update_yesterday_games.py',
        'Fetch completed games and player box scores'
    )

    # Step 2: Recalculate Coach stats
    print_header("Step 2/4: Recalculate Coach Stats")
    results['coaches'] = run_script(
        'calculate_coach_stats.py',
        'Update rotation depth, tempo, and coaching patterns'
    )

    # Step 3: Update Player attributes
    print_header("Step 3/4: Update Player Attributes")
    results['players'] = run_script(
        'expand_player_attributes.py',
        'Refresh impact, stamina, and style tags'
    )

    # Step 4: Lineup integrity check
    print_header("Step 4/4: Verify Lineup Integrity")
    results['lineups'] = run_script(
        'verify_lineups.py',
        'Check lineup data for missing players or roster changes'
    )

    # Summary
    print_header("Daily Update Summary")

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    for step, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {step.upper()}")

    print()
    print(f"  Results: {success_count}/{total_count} steps completed successfully")
    print()

    if success_count == total_count:
        print("  🎉 All systems updated! NBA v2.0 is ready for today's analysis.")
    elif success_count > 0:
        print("  ⚠️  Partial update completed. Review failures above.")
    else:
        print("  ❌ Update failed. Check error messages above.")

    print()
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()

    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
