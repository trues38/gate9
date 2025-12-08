#!/bin/bash
SEASONS=("2009-10" "2010-11" "2011-12" "2012-13")
echo "Starting Batch 1: 2009-2013"
for season in "${SEASONS[@]}"; do
    echo "========================================"
    echo "Crawling Season: $season"
    echo "========================================"
    python3 nba_data/pipeline/04_crawl_stories.py --season "$season"
done
echo "Batch 1 Complete"
