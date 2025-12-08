#!/bin/bash
SEASONS=("2013-14" "2014-15" "2015-16" "2016-17")
echo "Starting Batch 2: 2013-2017"
for season in "${SEASONS[@]}"; do
    echo "========================================"
    echo "Crawling Season: $season"
    echo "========================================"
    python3 nba_data/pipeline/04_crawl_stories.py --season "$season"
done
echo "Batch 2 Complete"
