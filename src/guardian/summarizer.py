from openai import OpenAI
from src.core.config import Config
from src.core.logger import logger

client = OpenAI(
    api_key=Config.OPENROUTER_API_KEY,
    base_url=Config.OPENROUTER_BASE_URL
)

def summarize_guard(text: str):
    """7B 문지기: 빠른 1차 요약"""
    prompt = f"""
    아래 내용을 1~2문장으로 요약해줘. 핵심만.

    내용:
    {text}
    """
    try:
        res = client.chat.completions.create(
            model=Config.MODEL_GUARD,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return res.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[Guard Summarizer Error] {e}")
        return None


def summarize_qc(summary: str):
    """14B QC: 정확도·문맥 보정"""
    prompt = f"""
    다음 요약을 더 정확하고 간결하게 다듬어줘.
    성급한 결론이나 오해 소지가 없도록 보정해줘.

    기존 요약:
    {summary}
    """
    try:
        res = client.chat.completions.create(
            model=Config.MODEL_QC,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return res.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[QC Error] {e}")
        return summary