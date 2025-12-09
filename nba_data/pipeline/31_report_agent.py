import os
import json
from openai import OpenAI

# Setup Client
# Assuming DEEPSEEK or OPENROUTER key is available
api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
base_url = "https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else "https://api.deepseek.com/v1"

client = OpenAI(api_key=api_key, base_url=base_url)

MODEL_NAME = "deepseek/deepseek-chat" # or similar

async def generate_report(terminal_data):
    """
    Takes 7-Layer JSON, calls LLM, returns HTML Report.
    """
    
    print("      [31_report_agent] Constructing Prompt from Layers...")
    
    # Construct Context
    context_str = json.dumps(terminal_data, indent=2)
    
    system_prompt = """You are REGIME PRO ANALYST.
Only use the data inside TERMINAL VIEW.
No hallucination. 
If something is missing, state “DATA NOT AVAILABLE”.
Your output must be a clean, semantic HTML document (no ```html blocks, just the raw html content starting with <article>). 
Use Tailwind CSS classes for styling. Theme: Dark Mode, High Contrast, Terminal Green/Amber.
"""

    user_prompt = f"""TERMINAL VIEW:
{context_str}

Generate a long-form analytical game report with the following structure:
1. EXECUTIVE OVERVIEW (Summary of the Vibe)
2. REGIME COLLISION MAP (Momentum vs Component)
3. PLAYER VECTOR ANALYSIS (Who is surging?)
4. REFEREE IMPACT (The Scott Foster Factor etc)
5. SCENARIO TREE (If A happens, then B)
6. CLOSING VERDICT (Confidence Score)

Format as a beautiful HTML Article.
"""

    print("      [31_report_agent] Calling LLM (DeepSeek)...")
    
    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1", # Attempting high reasoning model or standard
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # Strip fenced code blocks if present
        if "```html" in content:
            content = content.replace("```html", "").replace("```", "")
        
        return content
        
    except Exception as e:
        # Fallback for dev/demo if API fails (to prove flow works)
        import traceback
        print(f"      [31_report_agent] 🔴 API Error Details: {e}")
        print(traceback.format_exc())
        return mock_html_report(terminal_data)

def mock_html_report(data):
    """
    Returns a static HTML template if LLM fails, ensuring Zero Downtime.
    """
    meta = data['layer_1_meta']
    return f"""
    <article class="prose prose-invert max-w-none p-6 bg-slate-900 via-slate-800 to-black text-slate-300">
        <h1 class="text-3xl font-bold text-amber-500 mb-2">REGIME REPORT: {meta['home_team']} vs {meta['away_team']}</h1>
        <div class="text-xs font-mono text-slate-500 mb-8">ID: {meta['game_id']} | VENUE: {meta['venue']}</div>
        
        <section class="mb-8">
            <h2 class="text-xl font-bold text-green-400 border-b border-green-800 pb-2 mb-4">1. EXECUTIVE OVERVIEW</h2>
            <p>This is a fallback report generated because the Neural Engine is currently offline or unreachable.</p>
            <p><strong>Vegas Line:</strong> {meta['odds']['live']['spread']}</p>
        </section>

        <section class="mb-8">
            <h2 class="text-xl font-bold text-green-400 border-b border-green-800 pb-2 mb-4">2. DATA LAYERS</h2>
            <pre class="bg-black p-4 rounded text-xs font-mono text-green-300 overflow-auto">
{json.dumps(data['layer_2_team_regimes'], indent=2)}
            </pre>
        </section>
        
        <div class="p-4 bg-red-900/20 border border-red-800 rounded">
            <h3 class="font-bold text-red-500">SYSTEM NOTE</h3>
            <p class="text-sm">LLM Generation Failed. Displaying Raw Terminal Data.</p>
        </div>
    </article>
    """
