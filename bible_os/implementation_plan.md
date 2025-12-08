# Bible Meaning OS: KJV + WEB Implementation Plan

## Goal
Establish a robust Bible data foundation using two Public Domain versions:
1.  **KJV (King James Version)**: For rich metaphorical density and "Regime" detection.
2.  **WEB (World English Bible)**: For modern readability and clarity.

## User Review Required
> [!IMPORTANT]
> **Data Sources**: I will download JSON files from GitHub repositories (`scrollmapper/bible_databases` or `TehShrike/world-english-bible`).
> **Network Access**: Requires `curl` / `git` access to GitHub.

## Proposed Changes

### 1. Data Ingestion (JSON Based)
#### [NEW] `ingest_parallel.py`
- **Logic**:
    - Reads KJV JSON and WEB JSON.
    - Matches verses by standard Book-Chapter-Verse index.
    - Generates a unique ID: `[BOOK_ABBR]-[CH]-[VS]` (e.g., `GEN-1-1`).
    - Inserts into DuckDB.
- **Schema**:
    ```sql
    CREATE TABLE verses (
        id VARCHAR PRIMARY KEY,
        book VARCHAR,
        chapter INT,
        verse INT,
        text_kjv VARCHAR,
        text_web VARCHAR,
        text_kr_derived VARCHAR, -- Future Placeholder
        regime_tags VARCHAR[],
        embedding FLOAT[]
    );
    ```

### 2. File Cleanup
#### [DELETE] Old Korean TXT Logic
- Remove `ingest_bible.py` (the EUC-KR text parser).
- Clean `data/txt` directory if confirmed.

### 3. Regime Engine Update
- Update `regime_definitions.py` to include **English Keywords** drawn from KJV specific vocabulary (e.g., "wilderness", "desolate", "betray").

### 4. Meaning Engine Enhancement [NEXT]
- **Vector Search**: Implement cosine similarity search in `engine.py` to find verses semantically related to the user's query, not just by regime tag.
- **Korean Localization**: Update LLM prompts in `engine.py` to accept Korean queries and output Korean interpretations, acting as a translator/interpreter for the English Bible data.

## Verification Plan
### Automated Tests
1.  **Ingestion Verification**:
    - Run `ingest_parallel.py`.
    - Query: `SELECT text_kjv, text_web FROM verses WHERE id='GEN-1-1'`.
    - Verification: Ensure both columns are populated and match content-wise (In the beginning...).
2.  **Regime Tagging**:
    - Run tagging logic on "Psalm 23".
    - Verification: Should tag "Shepherd" (KJV) -> **R05/R17** (Guidance/Grace/Provider).
