# G9 Strategy RAG Pipeline

This pipeline generates 6 distinct investment strategies for each Macro Pattern using LLMs and syncs them to Supabase.

## 📂 File Structure
- `g9_rag/generate_strategies.py`: Main script.

## 🛠️ Configuration
The script uses `.env` for configuration:
- `OPENROUTER_API_KEY`: For LLM generation (GPT-4o/Claude) and Embeddings.
- `SUPABASE_URL`: Your Supabase project URL.
- `SUPABASE_KEY`: Your Supabase service role key.

## 🚀 Usage

Run the script directly with Python:

```bash
python3 g9_rag/generate_strategies.py
```

## 🧩 Features
- **Automated Strategy Generation**: Creates 6 strategies per pattern (Conservative, Moderate, Aggressive, Hedge, Risk Signals, Playbook).
- **Context-Aware**: Uses the full text of the pattern to generate specific, actionable strategies.
- **Vector Embedding**: Embeds the strategy content for semantic search.
- **Upsert Logic**: Updates existing strategies based on `strategy_id`.

## 📊 Database Schema
The script populates the `macro_strategies` table:

```sql
create extension if not exists vector;

create table if not exists macro_strategies (
  strategy_id text primary key, -- Format: {pattern_id}-{TYPE}
  pattern_id text,
  category text,
  title text,
  description text,
  rationale text,
  risk text,
  checklist text[],
  embedding vector(3072)
);
```

## 🔍 Strategy Types
1.  **Conservative**: Focus on capital preservation.
2.  **Moderate**: Balanced risk/reward.
3.  **Aggressive**: High alpha, high risk.
4.  **Hedge**: Protection against downside.
5.  **Risk Signals**: Early warning indicators.
6.  **Playbook**: Step-by-step execution guide.
