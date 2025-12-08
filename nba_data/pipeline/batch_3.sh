#!/bin/bash
SEASONS=("2017-18" "2018-19" "2019-20" "2020-21")
echo "Starting Batch 3: 2017-2021"
for season in "${SEASONS[@]}"; do
    echo "========================================"
    echo "Crawling Season: $season"
    echo "========================================"
    python3 nba_data/pipeline/04_crawl_stories.py --season "$season"
done
echo "Batch 3 Complete"
