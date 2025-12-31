"""
Local test script for Graph + Odds Report Generator
"""
import os
from graph_odds_report_generator import GraphOddsReportGenerator

# Configuration
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'your_password')
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

def test_single_game():
    """Test report generation for a single game"""
    print("\n" + "="*60)
    print("TEST: Single Game Report")
    print("="*60 + "\n")

    generator = GraphOddsReportGenerator(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        odds_api_key=ODDS_API_KEY,
        anthropic_api_key=ANTHROPIC_API_KEY
    )

    try:
        # Example: Lakers vs Warriors
        result = generator.generate_report_for_game(
            home_team='LAL',  # Lakers
            away_team='GSW'   # Warriors
        )

        if result['success']:
            print("\n✓ Report generated successfully!")
            print(f"File: {result['filepath']}")
            print(f"\nPreview:")
            print("="*60)
            print(result['report'][:500] + "...")
        else:
            print(f"\n✗ Failed: {result.get('error')}")

    finally:
        generator.close()


def test_odds_only():
    """Test odds fetching without graph"""
    print("\n" + "="*60)
    print("TEST: Odds API Only")
    print("="*60 + "\n")

    if not ODDS_API_KEY:
        print("ERROR: ODDS_API_KEY not set")
        return

    from odds_api_adapter import OddsAPIAdapter

    adapter = OddsAPIAdapter(api_key=ODDS_API_KEY)
    result = adapter.get_nba_odds(markets=['h2h', 'spreads'])

    if result['success']:
        print(f"✓ Found {len(result['games'])} games")

        # Show first game
        if result['games']:
            game = result['games'][0]
            print("\nFirst game:")
            print(adapter.format_odds_for_report(game))

        budget = adapter.get_budget_status()
        print(f"\nBudget: {budget['total_used']}/{budget['monthly_limit']} ({budget['usage_percent']}%)")
    else:
        print(f"✗ Error: {result.get('error')}")


def test_daily_batch():
    """Test generating reports for all today's games"""
    print("\n" + "="*60)
    print("TEST: Daily Batch Report Generation")
    print("="*60 + "\n")

    generator = GraphOddsReportGenerator(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        odds_api_key=ODDS_API_KEY,
        anthropic_api_key=ANTHROPIC_API_KEY
    )

    try:
        results = generator.generate_daily_report()

        success_count = sum(1 for r in results if r.get('success'))
        print(f"\n✓ Generated {success_count}/{len(results)} reports")

    finally:
        generator.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_local.py odds      # Test odds API only")
        print("  python test_local.py single    # Test single game report")
        print("  python test_local.py daily     # Test daily batch reports")
        sys.exit(1)

    test_type = sys.argv[1].lower()

    if test_type == 'odds':
        test_odds_only()
    elif test_type == 'single':
        test_single_game()
    elif test_type == 'daily':
        test_daily_batch()
    else:
        print(f"Unknown test type: {test_type}")
        sys.exit(1)
