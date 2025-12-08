#!/bin/bash
SEASONS=("2021-22" "2022-23" "2023-24" "2024-25")
echo "Starting Batch 4: 2021-2025"
for season in "${SEASONS[@]}"; do
    echo "========================================"
    echo "Crawling Season: $season"
    echo "========================================"
    python3 nba_data/pipeline/04_crawl_stories.py --season "$season"
done
echo "Batch 4 Complete"
