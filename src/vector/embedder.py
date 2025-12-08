from openai import OpenAI
from src.core.config import Config
from src.core.db import db
from src.core.logger import logger

client = OpenAI(
    api_key=Config.OPENROUTER_API_KEY,
    base_url=Config.OPENROUTER_BASE_URL
)

def embed_text(text: str):
    try:
        res = client.embeddings.create(
            model=Config.EMBED_MODEL,
            input=text
        )
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"[Embedding Error] {e}")
        return None

def save_embedding(event_id, embedding):
    try:
        db.table("events_vector").insert({
            "event_id": event_id,
            "embedding": embedding
        }).execute()
        logger.info(f"Saved vector for event {event_id}")
    except Exception as e:
        logger.error(f"[DB Error] {e}")