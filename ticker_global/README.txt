# Ticker Global - Data Pipeline Structure

This directory (`ticker_global`) manages the multi-country financial event data pipeline.

## Folder Structure

### 1. KR (Korea)
- **Path**: `ticker_global/KR/`
- **Description**: Contains scripts and data specific to the Korean market (KRX).
- **Key Scripts**:
    - `clean_and_dedup.py`: 
        - **Step 1**: Cleans headlines (removes ads, reporter names, special chars).
        - **Step 2**: Deduplicates events based on semantic similarity (grouping by Ticker + Date).
- **Data**:
    - `cleaned_events_final.csv`: The final, high-quality dataset ready for LLM analysis.

### 2. US (United States) - [Planned]
- **Path**: `ticker_global/US/`
- **Description**: Will contain scripts for NYSE/NASDAQ data.
- **Strategy**: Reuse the logic from KR but with English-specific regex and ticker maps.

## Usage Guide

1. **Raw Data Processing**:
   Run `process_jsonl_to_csv.py` in the root `g9` folder to generate the raw CSV (`merged_events_extended.csv`).

2. **Cleaning & Deduplication**:
   Run the country-specific cleaning script:
   ```bash
   python3 ticker_global/KR/clean_and_dedup.py
   ```

3. **LLM Analysis (Step 3)**:
   The output CSV from Step 2 is optimized for LLM input (low noise, high signal).
