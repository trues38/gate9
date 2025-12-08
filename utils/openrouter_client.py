import os
import json
import urllib.request
import urllib.error
import http.client
import time
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LLM = "x-ai/grok-4.1-fast:free"
MODEL_SQL = "x-ai/grok-4.1-fast:free"

def ask_llm(prompt, model=MODEL_LLM, system_prompt=None, api_key=None, base_url=None, **kwargs):
    # Normalize model to list for fallback support
    models = model if isinstance(model, list) else [model]
    
    for i, current_model in enumerate(models):
        if i > 0:
            print(f"🔄 Switching to backup model: {current_model}")

        # Check for Local Model
        if current_model.startswith("local/"):
            url = "http://localhost:11434/api/chat"
            real_model = current_model.replace("local/", "")
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": real_model,
                "messages": messages,
                "stream": False
            }
            # Merge kwargs for local model (e.g. temperature)
            data.update(kwargs)
            
            try:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as response:
                    if response.status == 200:
                        result = json.loads(response.read().decode('utf-8'))
                        return result['message']['content']
                    else:
                        print(f"⚠️ Local LLM Error {response.status}")
                        continue # Try next model
            except Exception as e:
                print(f"❌ Local LLM Failed: {e}")
                continue # Try next model

        # OpenRouter / Custom Logic
        url = base_url if base_url else "https://openrouter.ai/api/v1/chat/completions"
        key = api_key if api_key else OPENROUTER_API_KEY
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "G9-Engine/1.0"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": current_model,
            "messages": messages,
        }
        # Merge kwargs (temperature, response_format, etc.)
        data.update(kwargs)
        
        retries = 2 # Reduced retries per model since we have fallbacks
        backoff = 2
        
        model_success = False
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
                print(f"⚠️ LLM HTTP Error {e.code} (Attempt {attempt+1}/{retries}) with {current_model}: {error_body}")
                
                if e.code == 429 or e.code >= 500:
                    time.sleep(backoff * (attempt + 1))
                    continue
                else:
                    break # Client Error, try next model
            except (urllib.error.URLError, http.client.IncompleteRead) as e:
                print(f"⚠️ LLM Connection Error (Attempt {attempt+1}/{retries}) with {current_model}: {e}")
                time.sleep(backoff * (attempt + 1))
            except Exception as e:
                print(f"⚠️ LLM Unexpected Error (Attempt {attempt+1}/{retries}) with {current_model}: {e}")
                time.sleep(backoff * (attempt + 1))
        
        # If we get here, this model failed after retries. Loop continues to next model.
            
    print("❌ All models failed.")
    return None
