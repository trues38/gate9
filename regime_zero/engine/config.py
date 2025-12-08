from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RegimeConfig:
    domain_name: str
    assets: List[str]
    prompts: Dict[str, str]
    data_dir: str
    output_dir: str
    history_file: str
    
    # Optional: Override default window sizes per asset if needed
    window_days: Dict[str, int] = field(default_factory=dict)
