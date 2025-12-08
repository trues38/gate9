from supabase import create_client, ClientOptions
from src.core.config import Config

def get_db():
    opts = ClientOptions(schema="mm")
    return create_client(
        Config.SUPABASE_URL,
        Config.SUPABASE_KEY,
        options=opts
    )

db = get_db()