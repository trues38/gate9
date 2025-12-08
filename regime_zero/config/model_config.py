
# Regime Zero Model Configuration
# Defines the "Avengers Team" roles and their corresponding model stacks (Primary -> Backup -> Paid Fallback)

# 1. The Brain (Analysis, Regime Detection, Logic)
# Primary: Tongyi DeepResearch (User Request)
MODEL_BRAIN = [
    "alibaba/tongyi-deepresearch-30b-a3b:free",
    "allenai/olmo-3-32b-think:free",
    "openai/gpt-4o-mini"
]

# 2. The Storyteller (Narrative, Historical Twin, Reporting)
# Primary: TNG R1T Chimera (Creative, Character-based)
MODEL_STORYTELLER = [
    "tngtech/deepseek-r1t-chimera:free",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o-mini"
]

# 3. The Refiner (News Summary, Extraction, Fast Processing)
# Stage 1: Fast Filter (NVIDIA Nemotron / LongCat)
MODEL_REFINER_FAST = [
    "nvidia/nemotron-4-340b-instruct:free", # Using a known good ID, or the one user suggested if valid. User said "nvidia/nemotron-nano-9b-v2:free". Let's use that.
    "nvidia/nemotron-nano-9b-v2:free", 
    "google/gemini-2.0-flash-exp:free"
]

# Stage 2: Deep Analysis (Olmo 3 Think / Tongyi)
MODEL_REFINER_DEEP = [
    "allenai/olmo-3-32b-think:free",
    "alibaba/tongyi-deepresearch-30b-a3b:free",
    "google/gemini-2.0-flash-exp:free"
]

# 4. The Engineer (SQL, Code, Parsing)
# Primary: KAT Coder Pro V1 (Agentic Coding)
MODEL_ENGINEER = [
    "kwaipilot/kat-coder-pro:free",
    "openai/gpt-4o"
]

# 5. The Deep Diver (Research, Fact Checking, Context)
# Primary: Tongyi DeepResearch 30B (Deep Search)
MODEL_DEEP_DIVER = [
    "alibaba/tongyi-deepresearch-30b-a3b:free",
    "openai/o1-mini"
]

# Default Fallback
MODEL_DEFAULT = "openai/gpt-4o-mini"
