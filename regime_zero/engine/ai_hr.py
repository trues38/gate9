import sys
import os
import json
import random
import urllib.request
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

ROSTER_FILE = "regime_zero/config/model_roster.json"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Fallback Roster if API fails
DEFAULT_ROSTER = {
    "narrative": ["qwen/qwen-2.5-14b-instruct", "anthropic/claude-3-haiku", "meta-llama/llama-3-8b-instruct:free"],
    "quant": ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct", "mistralai/mistral-large"],
    "risk": ["x-ai/grok-beta", "google/gemini-2.0-flash-exp:free", "nousresearch/hermes-3-llama-3.1-405b"],
    "structure": ["openai/gpt-4o-mini", "microsoft/phi-3-medium-128k-instruct", "google/gemini-flash-1.5"],
    "news": ["google/gemini-flash-1.5", "perplexity/llama-3-sonar-large-32k-online", "openai/gpt-4o-mini"]
}

class AI_HR:
    def __init__(self):
        self.roster = self.load_roster()
        
    def load_roster(self):
        if os.path.exists(ROSTER_FILE):
            with open(ROSTER_FILE, "r") as f:
                return json.load(f)
        return DEFAULT_ROSTER

    def update_roster_from_openrouter(self):
        """
        Fetches the latest models from OpenRouter and categorizes them.
        """
        print("👔 HR: Updating Roster from OpenRouter...")
        try:
            req = urllib.request.Request(OPENROUTER_MODELS_URL)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            models = data.get('data', [])
            
            # Simple categorization logic (can be refined)
            new_roster = {k: [] for k in DEFAULT_ROSTER.keys()}
            
            for m in models:
                mid = m['id']
                name = m['name'].lower()
                
                # Categorize
                if "qwen" in name or "claude" in name:
                    new_roster["narrative"].append(mid)
                if "deepseek" in name or "llama-3-70b" in name or "math" in name:
                    new_roster["quant"].append(mid)
                if "grok" in name or "hermes" in name or "uncensored" in name:
                    new_roster["risk"].append(mid)
                if "gpt-4o" in name or "mini" in name or "flash" in name:
                    new_roster["structure"].append(mid)
                if "sonar" in name or "online" in name or "gemini" in name:
                    new_roster["news"].append(mid)
            
            # Merge with defaults to ensure we have basics
            for k in new_roster:
                new_roster[k] = list(set(new_roster[k] + DEFAULT_ROSTER[k]))
                
            self.roster = new_roster
            
            # Save
            os.makedirs(os.path.dirname(ROSTER_FILE), exist_ok=True)
            with open(ROSTER_FILE, "w") as f:
                json.dump(self.roster, f, indent=2)
                
            print(f"✅ HR: Roster Updated. Total Models: {sum(len(v) for v in self.roster.values())}")
            return True
            
        except Exception as e:
            print(f"❌ HR: Failed to update roster: {e}")
            return False

    def get_substitute(self, role, failed_model=None):
        """
        Returns a substitute model for the given role, excluding the failed one.
        """
        candidates = self.roster.get(role, [])
        
        # Filter out failed model
        if failed_model:
            candidates = [c for c in candidates if c != failed_model]
            
        if not candidates:
            # Fallback to a generic reliable list
            candidates = ["openai/gpt-4o-mini", "meta-llama/llama-3-8b-instruct:free"]
            
        sub = random.choice(candidates)
        print(f"👔 HR: Assigning Substitute for {role}: {sub}")
        return sub

if __name__ == "__main__":
    hr = AI_HR()
    hr.update_roster_from_openrouter()
    print(hr.get_substitute("news", "google/gemini-flash-1.5"))
