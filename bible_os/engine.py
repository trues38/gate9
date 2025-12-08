import os
import duckdb
import json
from openai import OpenAI
from dotenv import load_dotenv
from regime_definitions import REGIMES

# Load env
load_dotenv("../.env")

class MeaningEngine:
    def __init__(self, db_path="./data/db/bible.duckdb"):
        self.db_path = db_path
        self.con = duckdb.connect(db_path, read_only=True)
        
        # Init OpenAI
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = "gpt-4o-mini" # or similar fast model
        
    def identify_regime(self, user_query):
        """
        Classifies user query into top 3 probable regimes using LLM.
        """
        # Construct simplified regime list for prompt
        regime_list_str = "\n".join([f"{k}: {v['name']} - {v['desc']}" for k, v in REGIMES.items()])
        
        prompt = f"""
        You are a biblical counselor AI. Analyze the user's situation and map it to the most relevant Biblical Meaning Regimes.
        
        User Query: "{user_query}"
        
        Available Regimes:
        {regime_list_str}
        
        Select the top 1-3 regimes that best fit the emotional and situational context.
        Return ONLY a JSON array of regime codes, e.g. ["R01", "R03"].
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            print(f"DEBUG LLM Raw: {content}")
            data = json.loads(content)
            # Handle potential wrapping keys
            # Wrapper key check
            if "regimes" in data:
                return data["regimes"]
            
            # Direct list
            if isinstance(data, list):
                return data
                
            # Flat dict like {"R01": ..., "R02": ...}
            # We assume keys are the codes if they match R\d+ format, or values match.
            # Simple heuristic: return keys if they start with R, else values.
            keys = list(data.keys())
            if keys and keys[0].startswith("R"):
                return keys
                
            vals = list(data.values())
            if vals:
                # Value might be the list
                if isinstance(vals[0], list):
                    return vals[0]
                # Or value might be the code string
                if isinstance(vals[0], str) and vals[0].startswith("R"):
                    return vals
                    
            return []
        except Exception as e:
            print(f"Error in identify_regime: {e}")
            return []

    def get_embedding(self, text):
        try:
            response = self.client.embeddings.create(
                input=text,
                model="openai/text-embedding-3-small" if os.getenv("OPENROUTER_API_KEY") else "text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def retrieve_verses(self, query, regime_code, limit=3):
        """
        Retrieves verses using Vector Search (Semantic) + Regime Filter.
        If no embeddings, falls back to random sampling from Regime.
        """
        # 1. Try Vector Search
        query_vec = self.get_embedding(query)
        
        if query_vec:
            # DuckDB cosine similarity
            # New versions use list_cosine_similarity or array_cosine_similarity.
            # We'll try list_cosine_similarity as it's more standard for the list type.
            sql = f"""
            SELECT id, book_name, chapter, verse, text_kjv, text_web,
                   list_cosine_similarity(embedding, ?::FLOAT[]) as score
            FROM verses 
            WHERE list_contains(regime_tags, '{regime_code}') 
              AND embedding IS NOT NULL
            ORDER BY score DESC
            LIMIT {limit}
            """
            try:
                results = self.con.execute(sql, [query_vec]).fetchall()
                if results:
                    return [
                        {
                            "id": r[0],
                            "ref": f"{r[1]} {r[2]}:{r[3]}",
                            "text_kjv": r[4],
                            "text_web": r[5],
                            "score": r[6]
                        }
                        for r in results
                    ]
            except Exception as e:
                print(f"Vector search failed (likely no embeddings or old DuckDB version): {e}")

        # 2. Fallback: Random from Regime
        print("Falling back to random regime sampling...")
        query = f"""
        SELECT id, book_name, chapter, verse, text_kjv, text_web 
        FROM verses 
        WHERE list_contains(regime_tags, '{regime_code}')
        ORDER BY random()
        LIMIT {limit}
        """
        try:
            results = self.con.execute(query).fetchall()
            return [
                {
                    "id": r[0],
                    "ref": f"{r[1]} {r[2]}:{r[3]}",
                    "text_kjv": r[4],
                    "text_web": r[5]
                }
                for r in results
            ]
        except Exception as e:
            print(f"Error retrieving verses: {e}")
            return []

    def synthesize_interpretation(self, user_query, regime_code, verse_data):
        """
        Generates the final response in KOREAN.
        """
        regime_info = REGIMES.get(regime_code, {})
        regime_name = regime_info.get("name", "Unknown") # e.g. "광야 (The Wilderness)"
        
        prompt = f"""
        당신은 '성경 의미 해석 엔진(Bible Meaning Engine)'입니다. 
        사용자의 상황을 선택된 '레짐(Regime)'과 '성경 구절'을 통해 해석하고, 상담가처럼 따뜻하고 깊이 있는 통찰을 제공하세요.
        
        [Context]
        - 사용자 상황 (User Situation): "{user_query}"
        - 감지된 레짐 (Regime): {regime_name} ({regime_info.get('desc')})
        - 성경 구절 (Bible Verse): {verse_data['ref']} 
          (KJV): "{verse_data['text_kjv']}"
          (WEB): "{verse_data['text_web']}"
          
        [Instructions]
        모든 답변은 **한국어**로 작성하세요.
        다음 4가지 구조로 답변을 구성하세요:
        
        1. **공감과 반영 (Emotional Reflection)**: 사용자의 힘든 마음을 깊이 이해하고 공감하는 문장.
        2. **레짐의 의미 (Regime Interpretation)**: 지금 겪고 있는 이 상황이 성경적 원형(Archetype)인 '{regime_name}'의 관점에서 어떤 의미가 있는지 설명 (예: "지금은 단순히 길을 잃은 것이 아니라, 하나님만 의지하는 법을 배우는 광야의 시간입니다").
        3. **구절의 연결 (Verse Connection)**: 제시된 영어 성경 구절(KJV/WEB)의 의미를 한국어로 풀어서 설명하고, 사용자 상황에 적용. (영어 원문은 인용하지 말고 해석된 의미 위주로 전달).
        4. **실천적 방향 (Actionable Direction)**: 오늘 하루 붙잡아야 할 마음가짐이나 작은 실천 제안 (예언적이지 않고, 지혜/적용 중심).
        
        [Tone]
        - 따뜻하고, 깊이 있고, 영적인 통찰력이 느껴지는 어조.
        - 현대적이고 세련된 언어 사용 (지나친 종교적 상투어 배제).
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating interpretation: {e}"

if __name__ == "__main__":
    # Test with Korean Query
    engine = MeaningEngine()
    q = "너무 지치고 아무도 내 노력을 알아주지 않는 것 같아."
    print(f"Query: {q}")
    
    print("Identifying Regime...")
    regimes = engine.identify_regime(q)
    print(f"Regimes: {regimes}")
    
    if regimes:
        selected_regime = regimes[0]
        print(f"Selected: {selected_regime}")
        
        # Pass query to retrieve_verses for vector search
        verses = engine.retrieve_verses(q, selected_regime, limit=1)
        if verses:
            v = verses[0]
            print(f"Verse: {v['ref']}")
            if 'score' in v:
                print(f"Similarity Score: {v['score']}")
            
            print("Synthesizing...")
            resp = engine.synthesize_interpretation(q, selected_regime, v)
            print("\n=== RESPONSE ===\n")
            print(resp)
