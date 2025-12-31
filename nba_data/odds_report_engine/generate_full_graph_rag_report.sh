#!/bin/bash

##############################################
# Generate FULL Graph RAG + Odds Report
# Requires:
#   1. SSH Tunnel to VPS Neo4j (or direct connection)
#   2. Neo4j password
#   3. Anthropic API key
#   4. Odds API key
##############################################

set -e

echo "=========================================="
echo "Graph RAG + Odds Report Generator"
echo "=========================================="
echo ""

# Check environment variables
if [ -z "$ODDS_API_KEY" ]; then
    echo "ERROR: ODDS_API_KEY not set"
    echo "Run: export ODDS_API_KEY='b01049f1f29d61c53189799c40d66f69'"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    echo "Run: export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    echo "WARNING: NEO4J_PASSWORD not set"
    read -sp "Enter Neo4j password: " NEO4J_PASSWORD
    echo ""
    export NEO4J_PASSWORD
fi

# Check if SSH tunnel is needed
read -p "Use SSH tunnel to VPS Neo4j? (y/n): " USE_TUNNEL

if [ "$USE_TUNNEL" = "y" ]; then
    NEO4J_URI="bolt://localhost:7687"

    echo ""
    echo "Starting SSH tunnel in background..."
    echo "Run this in another terminal:"
    echo "  ./connect_vps_neo4j.sh"
    echo ""
    read -p "Press Enter when tunnel is ready..."
else
    # Direct connection to VPS
    NEO4J_URI="bolt://141.164.35.214:7687"
    echo "Using direct connection to VPS Neo4j"
fi

# Parse command arguments
if [ $# -eq 0 ]; then
    echo ""
    echo "Usage:"
    echo "  $0 daily             # All today's games"
    echo "  $0 HOME AWAY         # Specific matchup"
    echo ""
    echo "Examples:"
    echo "  $0 daily"
    echo "  $0 TOR GSW"
    exit 1
fi

MODE=$1

# Generate report
echo ""
echo "Generating Graph RAG + Odds report..."
echo "=========================================="
echo "Neo4j URI: $NEO4J_URI"
echo "Odds API: Enabled"
echo "Anthropic: Enabled"
echo "=========================================="
echo ""

case $MODE in
    "daily")
        python3 graph_odds_report_generator.py \
            --daily \
            --neo4j-uri "$NEO4J_URI" \
            --neo4j-password "$NEO4J_PASSWORD" \
            --odds-api-key "$ODDS_API_KEY" \
            --anthropic-api-key "$ANTHROPIC_API_KEY"
        ;;
    *)
        if [ $# -eq 2 ]; then
            HOME=$1
            AWAY=$2
            python3 graph_odds_report_generator.py \
                --home "$HOME" \
                --away "$AWAY" \
                --neo4j-uri "$NEO4J_URI" \
                --neo4j-password "$NEO4J_PASSWORD" \
                --odds-api-key "$ODDS_API_KEY" \
                --anthropic-api-key "$ANTHROPIC_API_KEY"
        else
            echo "ERROR: Invalid arguments"
            exit 1
        fi
        ;;
esac

echo ""
echo "✓ Report generated!"
echo ""
echo "View reports:"
echo "  ls -lht /Users/js/g9/nba_data/odds_reports/"
