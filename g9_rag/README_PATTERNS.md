# G9 Pattern Processing Pipeline

This pipeline automates the parsing, embedding, and syncing of Macro Pattern Markdown files to Supabase.

## 📂 File Structure
Place your pattern files in the `g9_rag` directory (or configured `PATTERN_DIR`).
Files should be named `P-XXX.md` (e.g., `P-001.md`).

## 🛠️ Configuration
The script uses `.env` for configuration:
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`: For generating embeddings (`text-embedding-3-large`).
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase service role key.

## 🚀 Usage

Run the script directly with Python:

```bash
python3 g9_rag/process_patterns.py
```

## 🧩 Features
- **Robust Parsing**: Handles various Markdown formats for Category, Title, Core, Triggers, and SQL Rules.
- **Full Text Embedding**: Embeds the entire content of the file for maximum context.
- **Upsert Logic**: Automatically updates existing patterns or inserts new ones based on `pattern_id`.
- **Retry Mechanism**: Includes exponential backoff for API calls and Database operations.
- **Integrity Check**: Reports success/failure counts and details.

## 📊 Database Schema
The script expects the following table in Supabase:

```sql
create extension if not exists vector;

create table if not exists macro_patterns (
  pattern_id text primary key,
  category text,
  title text,
  core text,
  triggers text[],
  sql_rules text,
  full_text text,
  embedding vector(3072)
);
```
