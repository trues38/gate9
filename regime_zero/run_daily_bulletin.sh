#!/bin/bash
# G9 Daily Bulletin Pipeline v3.5
# Yahoo Finance -> DVSS Validation -> State Engine -> Bulletin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATE=${1:-$(date +%Y-%m-%d)}

echo "========================================"
echo "  G9 Daily Bulletin Pipeline v3.5"
echo "  Date: $DATE"
echo "========================================"
echo ""

# Run bulletin generator
python3 engine/bulletin_generator_v35.py --date "$DATE"

echo ""
echo "========================================"
echo "  Pipeline Complete"
echo "========================================"
