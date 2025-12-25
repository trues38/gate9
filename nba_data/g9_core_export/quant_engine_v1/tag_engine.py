import pandas as pd
import numpy as np


# --- 4️⃣ Tag → Sentence Dictionary (Strict Mapping) ---
TAG_SENTENCES = {
    "FORM_SURGE": "최근 경기 흐름이 장기 평균 대비 뚜렷하게 개선되며 팀 컨디션이 살아난 모습이다.",
    "FORM_COLLAPSE": "최근 경기력은 장기 흐름 대비 명확한 하락 국면에 접어들었다.",
    "FAKE_MOMENTUM": "겉으로 보이는 성적과 달리 득실 마진이 동반되지 않아 경기 내용에는 의문이 따른다.",
    "FORM_REVERSAL": "장기적인 부진 속에서도 최근 경기력 반등의 신호가 감지된다.", 

    "NEMESIS_EDGE": "최근 맞대결에서 반복적으로 우위를 점해온 상성 구도가 확인된다.",
    "NEMESIS_TRAP": "전체 전력과 무관하게 이 상대를 만나면 고전하는 패턴이 반복되고 있다.",
    "RECENT_MATCHUP_SIGNAL": "최근 맞대결에서 우위를 보인 점이 심리적 이점으로 작용할 수 있다.", 

    "FATIGUE_TRAP": "짧은 휴식 일정으로 인해 체력 부담이 명확한 구간이다.",
    "SCHEDULE_ADVANTAGE": "상대보다 여유 있는 일정으로 체력적 우위를 기대할 수 있다.",

    "BLOWOUT_PROFILE": "득점력과 득실 마진 격차가 커 일방적인 경기 흐름으로 이어질 가능성이 높다.",
    "GRIND_GAME": "큰 점수 차 없이 접전 양상으로 전개될 가능성이 높은 경기다.",
    "PACE_MISMATCH": "양 팀의 템포 차이가 커 경기 운영 주도권이 승부의 변수가 될 전망이다.",

    "MARKET_OVERCONFIDENCE": "시장 배당이 실제 전력 대비 한쪽으로 과도하게 쏠려 있는 모습이다.",
    "MARKET_UNDERREACTION": "최근 경기력 변화가 배당에 충분히 반영되지 않은 구간이다.",
    "COIN_FLIP_GAME": "객관적 전력 차가 미미하여 당일 컨디션에 따라 승패가 갈릴 수 있는 '동전 던지기' 양상이다."
}

class TagEngine:
    """
    Engine for generating narrative tags based on quantitative conditions.
    """
    def __init__(self):
        pass

    def check_conditions(self, row):
        """
        Apply Boolean Logic to generate Tags.
        Python Only. No LLM.
        """
        tags = []
        
        # ---------------------------
        # 1. Feature Extraction (Safe Cast)
        # ---------------------------
        # Form
        avg_V_4 = row.get('avg_V_4', 0)
        avg_V_16 = row.get('avg_V_16', 0)
        avg_V_32 = row.get('avg_V_32', 0)
        avg_diff_P_4 = row.get('avg_diff_P_4', 0)
        avg_diff_P_8 = row.get('avg_diff_P_8', 0)
        avg_diff_P_16 = row.get('avg_diff_P_16', 0)
        avg_P_8 = row.get('avg_P_8', 0)
        avg_P_o_8 = row.get('avg_P_o_8', 0) 
        
        # Matchup
        score_10 = row.get('score_last_10_between', 0)
        score_5 = row.get('score_last_5_between', 0)
        
        # Schedule
        rest = row.get('days_since_last', 0)
        rest_o = row.get('days_since_last_o', 0)
        
        # Odds
        odds = row.get('odds', 0)
        
        # ---------------------------
        # 2. Logic Implementation
        # ---------------------------
        
        # 🔹 FORM / MOMENTUM
        if avg_V_4 > avg_V_16 + 0.15:
            tags.append("FORM_SURGE")
            
        if avg_V_4 < avg_V_16 - 0.15:
            tags.append("FORM_COLLAPSE")
            
        if avg_V_4 > avg_V_16 and avg_V_32 < 0.45:
            tags.append("FORM_REVERSAL")
            
        if avg_V_4 > 0.6 and avg_diff_P_4 < avg_diff_P_16:
            tags.append("FAKE_MOMENTUM")
            
        # 🔹 NEMESIS / MATCHUP
        if score_10 >= 6:
            tags.append("NEMESIS_EDGE")
            
        if score_10 <= -6:
            tags.append("NEMESIS_TRAP")
            
        if score_5 != 0:
            tags.append("RECENT_MATCHUP_SIGNAL")
            
        # 🔹 SCHEDULE / FATIGUE
        if rest <= 1 and rest_o >= 3:
            tags.append("FATIGUE_TRAP")
            
        if rest >= rest_o + 2:
            tags.append("SCHEDULE_ADVANTAGE")
            
        # 🔹 GAME SHAPE / FLOW
        if avg_diff_P_8 >= 8:
            tags.append("BLOWOUT_PROFILE")
            
        if abs(avg_diff_P_8) <= 2:
            tags.append("GRIND_GAME")
            
        # Pace Mismatch (Requires avg_P_8_o, assuming it exists or proxy)
        avg_P_8_o = row.get('avg_P_8_o', row.get('avg_P_o_8', 0)) 
        if abs(avg_P_8 - avg_P_8_o) >= 8:
            tags.append("PACE_MISMATCH")
            
        # 🔹 MARKET / ODDS
        if abs(avg_diff_P_8) < 2 and abs(odds) >= 7:
            tags.append("MARKET_OVERCONFIDENCE")
            
        if abs(avg_diff_P_8) >= 6 and abs(odds) <= 4:
            tags.append("MARKET_UNDERREACTION")
            
        if abs(avg_diff_P_8) <= 1 and abs(odds) <= 2:
            tags.append("COIN_FLIP_GAME")
            
        return tags

    def build_narrative(self, row):
        """
        Compiles the final narrative string.
        """
        tags = self.check_conditions(row)
        sentences = []
        
        for tag in tags:
            s = TAG_SENTENCES.get(tag)
            if s:
                sentences.append(s)
                
        # Default Fallback
        if not sentences:
            sentences.append("전력, 일정, 흐름 모두 평균 범위 내에 위치한 경기로 구조적 이탈은 관찰되지 않는다.")
            
        return " ".join(sentences), tags
