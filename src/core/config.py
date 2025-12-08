import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # LLM (문지기 = 7B, QC = 14B, 보고서 = High-end)
    MODEL_GUARD = os.getenv("MODEL_GUARD", "qwen/qwen-2.5-7b-instruct")
    MODEL_QC = os.getenv("MODEL_QC", "qwen/qwen-2.5-14b-instruct")
    MODEL_REPORT = os.getenv("MODEL_REPORT", "gpt-5.1")

    # Embedding
    EMBED_MODEL = os.getenv("EMBED_MODEL", "openai/text-embedding-3-large")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"