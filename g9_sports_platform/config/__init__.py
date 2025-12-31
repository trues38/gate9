"""
G9 Sports Platform - Configuration Module
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_DIR = Path(__file__).parent
SPORTS_DIR = Path(__file__).parent.parent / "sports"


def load_sport_config(sport: str) -> Dict[str, Any]:
    """
    스포츠별 설정 로드

    Args:
        sport: 스포츠 코드 (nba, nfl, mlb, epl, ufc)

    Returns:
        스포츠 설정 딕셔너리
    """
    config_path = SPORTS_DIR / sport / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Sport config not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_master_config() -> Dict[str, Any]:
    """마스터 설정 로드"""
    master_path = CONFIG_DIR / "sports.yaml"

    with open(master_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_enabled_sports() -> list:
    """활성화된 스포츠 목록 반환"""
    config = load_master_config()
    return [
        sport_code
        for sport_code, sport_config in config.get('sports', {}).items()
        if sport_config.get('enabled', False)
    ]
