#!/bin/bash

# List of seasons to crawl
SEASONS=(
    "2009-10"
    "2010-11"
    "2011-12"
    "2012-13"
    "2013-14"
    "2014-15"
    "2015-16"
    "2016-17"
    "2017-18"
    "2018-19"
    "2019-20"
    "2020-21"
    "2021-22"
    "2022-23"
    "2023-24"
    "2024-25"
)

echo "Starting Mass Crawl for ${#SEASONS[@]} seasons..."

for season in "${SEASONS[@]}"; do
    echo "========================================"
    echo "Crawling Season: $season"
    echo "========================================"
    python3 nba_data/pipeline/04_crawl_stories.py --season "$season"
    echo "Finished $season. Sleeping for 2 seconds..."
    sleep 2
done

echo "All seasons processed."
