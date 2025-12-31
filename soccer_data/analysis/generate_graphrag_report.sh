#!/bin/bash
# Graph RAG Enhanced Betting Report Generator
#
# This script generates NBA-level betting reports using Graph RAG context
#
# Usage:
#   ./generate_graphrag_report.sh [league]
#
# Examples:
#   ./generate_graphrag_report.sh          # Defaults to EPL
#   ./generate_graphrag_report.sh EPL
#   ./generate_graphrag_report.sh bundesliga

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

LEAGUE="${1:-EPL}"

echo "======================================================================"
echo "Graph RAG Enhanced Betting Report Generator"
echo "======================================================================"
echo ""
echo "League: $LEAGUE"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S UTC')"
echo ""
echo "======================================================================"
echo ""

# Check Neo4j connectivity
echo "Checking Neo4j connection..."
if ! nc -z localhost 7689 2>/dev/null; then
    echo "⚠️  Warning: Neo4j not running on localhost:7689"
    echo "   Graph RAG features will be unavailable"
    echo ""
    echo "   To start Neo4j:"
    echo "   - VPS: docker start g9-neo4j-soccer"
    echo "   - Local: SSH tunnel to VPS"
    echo ""
    exit 1
fi

echo "✅ Neo4j connected"
echo ""

# Generate Graph RAG report
echo "Generating Graph RAG enhanced report..."
echo "----------------------------------------------------------------------"
cd "$BASE_DIR"

python3 analysis/graph_rag_report_generator.py

if [ $? -ne 0 ]; then
    echo "❌ Report generation failed!"
    exit 1
fi

echo ""
echo "======================================================================"
echo "✅ Graph RAG Report Generated!"
echo "======================================================================"
echo ""

# Find the latest report
LATEST_MD=$(ls -t analysis/reports/graphrag_${LEAGUE,,}_*.md 2>/dev/null | head -1)

if [ -n "$LATEST_MD" ]; then
    echo "📄 Report: $LATEST_MD"
    echo ""
    echo "View report:"
    echo "  cat $LATEST_MD"
    echo ""
    echo "High-value bets:"
    grep -A 3 "High Value Bets" "$LATEST_MD" | tail -n +2 || echo "  (Check full report)"
    echo ""
else
    echo "⚠️  Report file not found"
fi

echo "======================================================================"
