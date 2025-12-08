import os
import time
import concurrent.futures
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("/Users/js/g9/.env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free", # Primary
    "qwen/qwen-2.5-72b-instruct:free",       # Alternative High-Spec Free
    "google/gemini-flash-1.5-8b",            # Fallback Fast (if free tier avail)
]

def test_call(model_name):
    print(f"🚀 Requesting {model_name}...")
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Say hello in 1 word."}],
        )
        dur = time.time() - start
        return f"✅ {model_name}: {resp.choices[0].message.content} ({dur:.2f}s)"
    except Exception as e:
        return f"❌ {model_name}: {e}"

def run_tests():
    print("Testing Parallel Execution...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(test_call, m): m for m in MODELS}
        for future in concurrent.futures.as_completed(futures):
            print(future.result())

if __name__ == "__main__":
    run_tests()
