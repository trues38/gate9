#!/bin/bash
# xG Betting Report Generation Pipeline
#
# This script runs the complete pipeline:
# 1. Validate xG data quality
# 2. Generate analysis (if validation passes)
# 3. Generate markdown reports
#
# Usage:
#   ./generate_betting_report.sh          # Full pipeline with prompts
#   ./generate_betting_report.sh --auto   # Auto-generate if validation passes

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

AUTO_MODE=false
if [[ "$1" == "--auto" ]]; then
    AUTO_MODE=true
fi

echo "======================================================================"
echo "xG Betting Report Generation Pipeline"
echo "======================================================================"
echo ""

# Step 1: Validate data
echo "Step 1/3: Validating xG data..."
echo "----------------------------------------------------------------------"

cd "$BASE_DIR"
python3 analysis/validate_xg_data.py

VALIDATION_EXIT_CODE=$?

echo ""

if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
    echo "❌ Validation failed!"
    echo ""
    echo "Please fix the errors above before generating reports."
    echo "Common fixes:"
    echo "  - Run xG collection: python3 scripts/understat_selenium_collector.py"
    echo "  - Check database: sqlite3 data/soccer.db"
    exit 1
fi

echo "✅ Validation passed!"
echo ""

# Step 2: Generate analysis
if [ "$AUTO_MODE" = true ]; then
    PROCEED="y"
else
    echo "Step 2/3: Generate xG analysis?"
    echo "This will analyze xG data for all leagues (takes ~10 seconds)"
    read -p "Proceed? (y/n): " PROCEED
fi

if [[ "$PROCEED" =~ ^[Yy]$ ]]; then
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Generating analysis..."
    echo "----------------------------------------------------------------------"
    python3 analysis/xg_betting_analyzer.py

    if [ $? -ne 0 ]; then
        echo "❌ Analysis generation failed!"
        exit 1
    fi

    echo ""
    echo "✅ Analysis generated!"
    echo ""
else
    echo "Skipping analysis generation."
    exit 0
fi

# Step 3: Generate reports
if [ "$AUTO_MODE" = true ]; then
    PROCEED="y"
else
    echo "Step 3/3: Generate betting reports?"
    echo "This will create markdown reports for all leagues"
    read -p "Proceed? (y/n): " PROCEED
fi

if [[ "$PROCEED" =~ ^[Yy]$ ]]; then
    echo ""
    echo "----------------------------------------------------------------------"
    echo "Generating reports..."
    echo "----------------------------------------------------------------------"
    python3 analysis/xg_report_generator.py

    if [ $? -ne 0 ]; then
        echo "❌ Report generation failed!"
        exit 1
    fi

    echo ""
    echo "======================================================================"
    echo "✅ Pipeline Complete!"
    echo "======================================================================"
    echo ""
    echo "Reports generated in: analysis/reports/"
    echo ""
    echo "View summary report:"
    echo "  cat analysis/reports/xg_summary_*.md"
    echo ""
    echo "View EPL report:"
    echo "  cat analysis/reports/xg_epl_*.md"
    echo ""
else
    echo "Skipping report generation."
    exit 0
fi
