from regime_zero.engine.config import RegimeConfig
from regime_zero.prompts.asset_regime_prompts import BTC_REGIME_PROMPT, FED_REGIME_PROMPT, OIL_REGIME_PROMPT, GOLD_REGIME_PROMPT, NEWS_REGIME_PROMPT

ECONOMY_CONFIG = RegimeConfig(
    domain_name="economy",
    assets=["BTC", "FED", "OIL", "GOLD", "NEWS"],
    prompts={
        "BTC": BTC_REGIME_PROMPT,
        "FED": FED_REGIME_PROMPT,
        "OIL": OIL_REGIME_PROMPT,
        "GOLD": GOLD_REGIME_PROMPT,
        "NEWS": NEWS_REGIME_PROMPT
    },
    data_dir="regime_zero/data/regimes",
    output_dir="regime_zero/data/regimes",
    history_file="regime_zero/data/multi_asset_history/unified_history.csv",
    window_days={
        "FED": 30,
        "NEWS": 3
    }
)
