#!/usr/bin/env python3
"""
G9 Bulletin Generator (Unified)
================================
핵심만 남긴 통합 파이프라인

사용법:
    python3 generate_bulletin.py --date 2025-12-30

파이프라인:
    [DVSS] → [State Engine] → [Bulletin]
       ↓           ↓              ↓
    검증된 데이터 → 실시간 상태 → 일관된 보고서
"""

import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "engine"))
sys.path.insert(0, os.path.join(BASE_DIR, "engine", "state_graph"))

from unified_pipeline import UnifiedPipeline, _build_bulletin_from_result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="G9 Unified Bulletin Generator")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"G9 UNIFIED BULLETIN GENERATOR")
    print(f"Date: {args.date}")
    print(f"{'='*60}\n")

    # Run pipeline
    pipeline = UnifiedPipeline(verbose=not args.quiet)
    result = pipeline.run(args.date)

    if not result["success"]:
        print(f"\n🔴 FAILED: {result.get('error')}")
        return 1

    # Generate bulletin
    bulletin = _build_bulletin_from_result(result)

    # Save bulletin
    output_dir = os.path.join(BASE_DIR, "reports/bulletins")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"BULLETIN_{args.date}.md")

    with open(output_path, 'w') as f:
        f.write(bulletin)

    print(f"\n{'='*60}")
    print(f"✅ Bulletin saved: {output_path}")
    print(f"{'='*60}\n")

    # Print bulletin
    print(bulletin)

    return 0


if __name__ == "__main__":
    exit(main())
