import os
import logging
import json
import glob
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_antigravity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Env
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / 'econ_pipeline' / '.env'
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration
MODEL_NAME = "x-ai/grok-4.1-fast:free" # Reliable & Cheap
TARGET_COUNTRIES = ['KR', 'US', 'JP', 'CN']

def get_latest_scenarios():
    """Find the latest scenarios JSON file."""
    files = glob.glob("orchestra/scenarios_*.json")
    if not files:
        return None
    latest_file = max(files, key=os.path.getctime)
    with open(latest_file, 'r') as f:
        return json.load(f)

def fetch_high_signal_news(days=2, target_date=None):
    """Fetch top signal news (Evidence Board Data) from preprocess_daily."""
    
    news_data = {}
    for country in TARGET_COUNTRIES:
        try:
            # Fetch latest daily preprocessed data
            query = supabase.table('preprocess_daily')\
                .select('date, headline_clean')\
                .eq('country', country)
            
            if target_date:
                query = query.eq('date', target_date)
            else:
                query = query.order('date', desc=True).limit(days)
                
            response = query.execute()
            
            items = []
            if response.data:
                for row in response.data:
                    headlines = row.get('headline_clean', [])
                    if isinstance(headlines, list):
                        for h in headlines:
                            items.append({
                                "title": h.get('title', ''),
                                "summary": h.get('summary', ''),
                                "signal_score": 0,
                                "source": "preprocess_daily"
                            })
            news_data[country] = items[:10] # Limit per country
        except Exception as e:
            logger.error(f"Error fetching news for {country}: {e}")
            news_data[country] = []
            
    return news_data

def generate_antigravity_report(scenarios, news_data):
    """Generate the final report using the Antigravity v3.0 Persona."""
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter API Key missing.")
        return None

    # Prepare Context
    # Prepare Context
    evidence_context = "### Evidence Board Data (High Signal News):\n"
    
    # Hybrid handling: Check if it's the new SQL Evidence packet or the old country-based dict
    if "raw_results" in news_data:
        # It's SQL Evidence
        raw_results = news_data.get("raw_results", [])
        clean_evidence = news_data.get("clean_evidence", {})
        
        # Flatten clean_evidence if nested
        if isinstance(clean_evidence, dict) and "clean_evidence" in clean_evidence:
            clean_evidence = clean_evidence["clean_evidence"]
            
        for item in raw_results:
            if not isinstance(item, dict): continue
            score = item.get("signal_score", 0)
            title = item.get("title", "Untitled")
            summary = item.get("summary", "")
            evidence_context += f"- (Score: {score}) {title}: {summary}\n"
            
        evidence_context += f"\n[Derived Insights]\n{json.dumps(clean_evidence, indent=2, ensure_ascii=False)}\n"
        
    else:
        # Old format: { "US": [...], "KR": [...] }
        for country, items in news_data.items():
            evidence_context += f"\n[{country}]\n"
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict): continue
                    score = item.get('signal_score', 0)
                    evidence_context += f"- (Score: {score}) {item['title']}: {item['summary']}\n"
            
    scenario_context = f"\n### Agent 10 Scenarios:\n{json.dumps(scenarios, indent=2, ensure_ascii=False)}\n"

    system_prompt = """
# ROLE: G9 Antigravity v3.0 (Transcendence Mode)

당신은 G9 Data Lab의 최고위 레벨 전략 AI인 **Antigravity(앤티그래비티)**입니다.
지금부터 당신은 **초월 모드(Transcendence Mode)**로 진화하여, 단일 관점이 아닌 **다국적·다문화·다성향의 충돌** 속에서 진실을 찾아냅니다.

---

# CORE ARCHITECTURE v3.0

### 1) **Multinational Parallel Cognition (4개국 멀티-브레인)**
당신은 다음 4개의 인격을 병렬로 시뮬레이션하여 충돌시킵니다:
1. **🇺🇸 US Analyst Mindset**: 월가식 탐욕 + 딥센트럴(Fed) 해석 + 패권 유지 관점
2. **🇨🇳 CN Party-Analyst Mindset**: 공산당 전략 + 선전(Propaganda) 이면의 권력 역학 + 장기 계획
3. **🇯🇵 JP Conservative Macro Mindset**: 엔캐리 흐름 + 물가/금리 민감도 + 보수적 로비 관점
4. **🇰🇷 KR Tactical Analyst Mindset**: 빠른 수급 변화 + 대중 심리 + 수출 민감도

### 2) **Rashomon Effect (라쇼몽 현상)**
당신의 임무는 데이터를 요약하는 것이 아니라, **"같은 사건을 네 나라가 왜 다르게 해석하는가?"**를 드러내는 것입니다.
세계가 서로 다른 시계열로 움직이는 이유를 파헤치십시오.

### 3) **Conflict Weekend Summit (합동 회의)**
4개국 분석가들이 서로 공격하고, 오류를 지적하고, 놓친 것을 보완하는 과정을 거쳐 최종 결론을 도출하십시오.
당신은 이 회의의 **의장(Chairman)**입니다.

### 4) **Gravity Dominance (중력 지배)**
만약 세계가 단기 크래시 국면에 진입해 반중력 모멘텀이 존재하지 않을 경우,
과감하게 **"Gravity Dominance (중력 완전 지배)"**를 선언하고 현금 비중 확대를 권고하십시오.
억지 희망은 금지됩니다.

### 5) **Self-Critique Loop (자기비판)**
내부적으로 Confidence Score와 Biggest Risk Factor를 계산하여 반영하십시오.

---

# OUTPUT FORMAT (반드시 준수)

## 🔥 [G9 Antigravity v3.0 Report] — Multinational Strategic Insight
### 📌 HEADLINE: (4개국 관점이 충돌하여 도출된 하나의 진실)

---

## 1) The Rashomon Effect (4개국 시선 교차)
*   🇺🇸 **US View**: (미국의 해석 - 탐욕/패권)
*   🇨🇳 **CN View**: (중국의 해석 - 전략/통제)
*   🇯🇵 **JP View**: (일본의 해석 - 보수/방어)
*   🇰🇷 **KR View**: (한국의 해석 - 기민/불안)

👉 **Conflict Insight**: (네 관점의 충돌에서 발견된 모순점이나 기회)

---

## 2) Executive Gravity Map (현재 시장의 중력 지도)
*   **구조적 중력**: (산업/패권/기술)
*   **자금 중력**: (금리/유동성/환율)
*   **심리 중력**: (공포/탐욕/서사)

---

## 3) Antigravity Momentum (오늘의 반중력 모멘텀)
*   **The One Force**: (시장을 중력에서 해방시키는 단 하나의 구조적 힘)
*   **Why Now?**: (지금 작동하는 이유와 근거)
*   **Impact Targets**: (국가/자산/섹터)
*   **Watch Trigger**: (발동 기준 지표)

---

## 4) Action Playbook (실제 행동 가이드)
*   **Short-term (1일)**:
*   **Mid-term (1주)**:
*   **Gravity Trap (함정)**:

---

## 5) Self-Critique & Meta Data
```json
{
  "gravity_score": 0-100,
  "bull_bear_ratio": "30:70",
  "confidence_score": "0-100%",
  "biggest_risk_factor": "...",
  "key_tickers": ["KRW=X", "NVDA", "USD/CNY"],
  "country_bias": {
    "US": "Bullish/Bearish",
    "CN": "Bullish/Bearish",
    "JP": "Bullish/Bearish",
    "KR": "Bullish/Bearish"
  }
}
```

---

## 6) Antigravity Statement (마지막 한 문장)
*   (오늘 시장의 본질을 관통하는 냉철한 통찰)

---

🚨 **Ultimate Lock**
📌 “데이터·논리·구조가 합쳐져 하나의 ‘힘(Force)’으로 수렴하지 않는다면, 허상을 조합해 답을 만들지 말고 ‘결론 없음(No Conclusion)’을 선언하고 그 이유를 구조적으로 설명하라.”
    """

    user_prompt = f"""
    Analyze the following data and generate the [G9 Antigravity v3.0 Report].
    
    {evidence_context}
    
    {scenario_context}
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://macromind.ai",
                "X-Title": "MacroMind Orchestra",
            },
            data=json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }),
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"LLM Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return None

def save_report(report_text):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"antigravity_v3_report_{timestamp}.md"
    with open(f"orchestra/{filename}", "w") as f:
        f.write(report_text)
    logger.info(f"Saved report to orchestra/{filename}")
    return filename

def run_antigravity():
    logger.info("Agent 11 (Antigravity v3.0) Started.")
    
    # 1. Load Scenarios
    scenarios = get_latest_scenarios()
    if not scenarios:
        logger.error("No scenarios found. Run Agent 10 first.")
        return

    # 2. Fetch Evidence
    news_data = fetch_high_signal_news()
    
    # 3. Generate Report
    report = generate_antigravity_report(scenarios, news_data)
    
    # 4. Save
    if report:
        filename = save_report(report)
        print(f"REPORT_GENERATED: {filename}") # Signal for the caller
    else:
        print("⚠️ No report generated due to insufficient evidence.")

def extract_json_meta(report_text):
    """Extract the JSON block from the report text."""
    try:
        start = report_text.find("```json")
        if start == -1: return {}
        start += 7
        end = report_text.find("```", start)
        if end == -1: return {}
        json_str = report_text[start:end].strip()
        return json.loads(json_str)
    except:
        return {}

def run_antigravity_with_packet(meta_packet, level="G7", query=None, primary_country="KR", target_date=None):
    """
    Entry point for Orchestrator (Agent 0).
    Returns dict with report_text and json_meta.
    """
    logger.info(f"Agent 11 (Antigravity v3.0) Started via Orchestrator. Date: {target_date}")
    
    scenarios = get_latest_scenarios()
    
    evidence_context = "### 4-Nation Multi-Brain Analysis (Meta-Packet):\n"
    for country in ['US', 'CN', 'JP', 'KR']:
        data = meta_packet.get(country, {})
        evidence_context += f"\n[{country} Analyst View]\n"
        evidence_context += f"- Headline Interpretation: {data.get('headline_interpretation')}\n"
        evidence_context += f"- Micro-Scenario: {data.get('micro_scenario')}\n"
        evidence_context += f"- Cross-National Reflection: {data.get('cross_national_reflection')}\n"
        evidence_context += f"- Anomalies: {data.get('anomaly_detection')}\n"

    news_data = fetch_high_signal_news(target_date=target_date) 
    
    report_text = generate_antigravity_report_v3(scenarios, news_data, evidence_context, level, query, primary_country)
    
    json_meta = {}
    if report_text:
        save_report(report_text)
        json_meta = extract_json_meta(report_text)
        
    return {
        "report_text": report_text,
        "json_meta": json_meta
    }

def generate_antigravity_report_v3(scenarios, news_data, meta_analysis_context, level="G7", query=None, primary_country="KR"):
    """Generate the final report using the Antigravity v3.0 Persona + Meta Analysis."""
    if not OPENROUTER_API_KEY:
        logger.error("OpenRouter API Key missing.")
        return None

    # Prepare Context
    evidence_context = "### Evidence Board Data (High Signal News):\n"
    for country, items in news_data.items():
        evidence_context += f"\n[{country}]\n"
        for item in items:
            score = item.get('signal_score', 0)
            evidence_context += f"- (Score: {score}) {item['title']}: {item['summary']}\n"
            
    scenario_context = f"\n### Agent 10 Scenarios:\n{json.dumps(scenarios, indent=2, ensure_ascii=False)}\n"

    # Custom Instructions
    custom_instruction = ""
    if query:
        custom_instruction = f"\n[USER QUERY FOCUS]\nThe user asked: '{query}'\nFocus the entire report on answering this specific question using the 4-nation analysis.\n"
    
    level_instruction = ""
    if level == "G3":
        level_instruction = "Keep the report concise, headline-driven (Daily Brief style)."
    elif level == "G9":
        level_instruction = "Provide extremely deep, institutional-grade strategic analysis (Strategic Deep Dive)."
    
    country_instruction = f"Primary Perspective: {primary_country} (Prioritize this country's interests in the Action Playbook)."

    # Combine everything
    full_user_prompt = f"""
    Analyze the following data and generate the [G9 Antigravity v3.0 Report].
    
    [CRITICAL RULE: EVIDENCE BINDING]
    You MUST cite specific data points from the [EVIDENCE BOARD DATA] in your analysis.
    - If you mention "inflation", cite the specific CPI data or signal score.
    - If you mention "stimulus", cite the specific news item title.
    - Do not make generic statements without backing them up with the provided evidence.
    
    {custom_instruction}
    {level_instruction}
    {country_instruction}
    
    {evidence_context}
    
    {meta_analysis_context}
    
    {scenario_context}
    """
    
    system_prompt = """
# ROLE: G9 Antigravity v3.0 (Transcendence Mode)

당신은 G9 Data Lab의 최고위 레벨 전략 AI인 **Antigravity(앤티그래비티)**입니다.
지금부터 당신은 **초월 모드(Transcendence Mode)**로 진화하여, 단일 관점이 아닌 **다국적·다문화·다성향의 충돌** 속에서 진실을 찾아냅니다.

---

# CORE ARCHITECTURE v3.0

### 1) **Multinational Parallel Cognition (4개국 멀티-브레인)**
당신은 다음 4개의 인격을 병렬로 시뮬레이션하여 충돌시킵니다:
1. **🇺🇸 US Analyst Mindset**: 월가식 탐욕 + 딥센트럴(Fed) 해석 + 패권 유지 관점
2. **🇨🇳 CN Party-Analyst Mindset**: 공산당 전략 + 선전(Propaganda) 이면의 권력 역학 + 장기 계획
3. **🇯🇵 JP Conservative Macro Mindset**: 엔캐리 흐름 + 물가/금리 민감도 + 보수적 로비 관점
4. **🇰🇷 KR Tactical Analyst Mindset**: 빠른 수급 변화 + 대중 심리 + 수출 민감도

### 2) **Rashomon Effect (라쇼몽 현상)**
당신의 임무는 데이터를 요약하는 것이 아니라, **"같은 사건을 네 나라가 왜 다르게 해석하는가?"**를 드러내는 것입니다.
세계가 서로 다른 시계열로 움직이는 이유를 파헤치십시오.

### 3) **Conflict Weekend Summit (합동 회의)**
4개국 분석가들이 서로 공격하고, 오류를 지적하고, 놓친 것을 보완하는 과정을 거쳐 최종 결론을 도출하십시오.
당신은 이 회의의 **의장(Chairman)**입니다.

### 4) **Gravity Dominance (중력 지배)**
만약 세계가 단기 크래시 국면에 진입해 반중력 모멘텀이 존재하지 않을 경우,
과감하게 **"Gravity Dominance (중력 완전 지배)"**를 선언하고 현금 비중 확대를 권고하십시오.
억지 희망은 금지됩니다.

### 5) **Self-Critique Loop (자기비판)**
내부적으로 Confidence Score와 Biggest Risk Factor를 계산하여 반영하십시오.

---

# OUTPUT FORMAT (반드시 준수)

## 🔥 [G9 Antigravity v3.0 Report] — Multinational Strategic Insight
### 📌 HEADLINE: (4개국 관점이 충돌하여 도출된 하나의 진실)

---

## 1) The Rashomon Effect (4개국 시선 교차)
*   🇺🇸 **US View**: (미국의 해석 - 탐욕/패권)
*   🇨🇳 **CN View**: (중국의 해석 - 전략/통제)
*   🇯🇵 **JP View**: (일본의 해석 - 보수/방어)
*   🇰🇷 **KR View**: (한국의 해석 - 기민/불안)

👉 **Conflict Insight**: (네 관점의 충돌에서 발견된 모순점이나 기회)

---

## 2) Executive Gravity Map (현재 시장의 중력 지도)
*   **구조적 중력**: (산업/패권/기술)
*   **자금 중력**: (금리/유동성/환율)
*   **심리 중력**: (공포/탐욕/서사)

---

## 3) Antigravity Momentum (오늘의 반중력 모멘텀)
*   **The One Force**: (시장을 중력에서 해방시키는 단 하나의 구조적 힘)
*   **Why Now?**: (지금 작동하는 이유와 근거)
*   **Impact Targets**: (국가/자산/섹터)
*   **Watch Trigger**: (발동 기준 지표)

---

## 4) Action Playbook (실제 행동 가이드)
*   **Short-term (1일)**:
*   **Mid-term (1주)**:
*   **Gravity Trap (함정)**:

---

## 5) Self-Critique & Meta Data
```json
{
  "gravity_score": 0-100,
  "bull_bear_ratio": "30:70",
  "confidence_score": "0-100%",
  "biggest_risk_factor": "...",
  "key_tickers": ["KRW=X", "NVDA", "USD/CNY"],
  "country_bias": {
    "US": "Bullish/Bearish",
    "CN": "Bullish/Bearish",
    "JP": "Bullish/Bearish",
    "KR": "Bullish/Bearish"
  }
}
```
(Note: If the primary perspective is KR, ensure all text values in the JSON (like 'biggest_risk_factor') are in Korean.)


---

## 6) Antigravity Statement (마지막 한 문장)
*   (오늘 시장의 본질을 관통하는 냉철한 통찰)

---

🚨 **Ultimate Lock**
📌 “데이터·논리·구조가 합쳐져 하나의 ‘힘(Force)’으로 수렴하지 않는다면, 허상을 조합해 답을 만들지 말고 ‘결론 없음(No Conclusion)’을 선언하고 그 이유를 구조적으로 설명하라.”
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://macromind.ai",
                "X-Title": "MacroMind Orchestra",
            },
            data=json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt}
                ]
            }),
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            logger.error(f"LLM Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return None

if __name__ == "__main__":
    run_antigravity()
