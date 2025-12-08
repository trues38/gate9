import os
import json
import urllib.request
import urllib.error
import http.client
import time
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LLM = "openai/gpt-4o-mini"
MODEL_SQL = "google/gemini-flash-1.5"

def ask_llm(prompt, model=MODEL_LLM, system_prompt=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "User-Agent": "G9-Engine/1.0"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": model,
        "messages": messages,
    }
    
    retries = 3
    backoff = 2
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    return result['choices'][0]['message']['content']
                else:
                    print(f"⚠️ LLM Error {response.status}: {response.read()}")
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode('utf-8')
            except:
                error_body = "Unknown Error Body"
            print(f"⚠️ LLM HTTP Error {e.code} (Attempt {attempt+1}/{retries}): {error_body}")
            
            if e.code == 429 or e.code >= 500:
                time.sleep(backoff * (attempt + 1))
                continue
            else:
                break # Client Error
        except (urllib.error.URLError, http.client.IncompleteRead) as e:
            print(f"⚠️ LLM Connection Error (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(backoff * (attempt + 1))
        except Exception as e:
            print(f"⚠️ LLM Unexpected Error (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(backoff * (attempt + 1))
            
    print("❌ LLM Failed after retries.")
    return None
