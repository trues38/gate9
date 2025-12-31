#!/bin/bash

##############################################
# Quick Report Generator
# Usage:
#   ./generate_report.sh daily          # 오늘 전체 경기
#   ./generate_report.sh LAL GSW        # 특정 경기
#   ./generate_report.sh test           # 테스트 모드
##############################################

set -e  # Exit on error

# Check environment variables
if [ -z "$ODDS_API_KEY" ]; then
    echo "ERROR: ODDS_API_KEY not set"
    echo "Run: export ODDS_API_KEY='your_key'"
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    echo "WARNING: NEO4J_PASSWORD not set. Using default."
    NEO4J_PASSWORD="your_password"
fi

# Parse arguments
if [ $# -eq 0 ]; then
    echo "Usage:"
    echo "  $0 daily             # Generate reports for all today's games"
    echo "  $0 HOME AWAY         # Generate report for specific matchup"
    echo "  $0 test              # Run test mode (odds only)"
    echo ""
    echo "Examples:"
    echo "  $0 daily"
    echo "  $0 LAL GSW"
    echo "  $0 test"
    exit 1
fi

MODE=$1

case $MODE in
    "daily")
        echo "Generating daily reports for all games..."
        python3 graph_odds_report_generator.py \
            --daily \
            --neo4j-password "$NEO4J_PASSWORD" \
            --odds-api-key "$ODDS_API_KEY" \
            --anthropic-api-key "${ANTHROPIC_API_KEY:-}"
        ;;

    "test")
        echo "Running test mode (odds only)..."
        python3 test_local.py odds
        ;;

    *)
        if [ $# -eq 2 ]; then
            HOME=$1
            AWAY=$2
            echo "Generating report for $AWAY @ $HOME..."
            python3 graph_odds_report_generator.py \
                --home "$HOME" \
                --away "$AWAY" \
                --neo4j-password "$NEO4J_PASSWORD" \
                --odds-api-key "$ODDS_API_KEY" \
                --anthropic-api-key "${ANTHROPIC_API_KEY:-}"
        else
            echo "ERROR: Invalid arguments"
            echo "Usage: $0 HOME AWAY"
            echo "Example: $0 LAL GSW"
            exit 1
        fi
        ;;
esac

echo ""
echo "✓ Complete!"
echo ""
echo "Reports saved to: /Users/js/g9/nba_data/odds_reports/"
ls -lht /Users/js/g9/nba_data/odds_reports/ | head -5
