"""NBA Daily Betting Report Generator - 진입점"""

import json
import os
from agents import structural_analyst, pattern_matcher, market_decision, report_editor, regime_logger


def main():
    # 1. 입력 로드
    input_path = "input/sample_input.json"
    with open(input_path, "r") as f:
        raw_data = json.load(f)

    print("Step 1: Structural Analyst")
    structural_output = structural_analyst.analyze(raw_data)

    print("Step 2: Pattern Matcher")
    pattern_output = pattern_matcher.analyze(structural_output)

    print("Step 3: Market & Decision")
    decision_output = market_decision.analyze(pattern_output)

    print("Step 4: Report Editor")
    report_md = report_editor.generate(structural_output, pattern_output, decision_output)

    # 2. 출력 저장
    output_path = "output/Daily_Report.md"
    os.makedirs("output", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report_md)

    print(f"\n✓ Report generated: {output_path}")

    # 3. Regime 관찰 로그 (passive, not used in v0.1)
    # This accumulates data for future regime discovery
    # Does NOT influence current pipeline decisions
    log_result = regime_logger.log_observations(
        game_patterns=pattern_output.get("game_patterns", []),
        betting_decisions=decision_output.get("betting_decisions", []),
        game_contexts=structural_output.get("game_contexts", [])
    )

    if log_result.get("status") == "success":
        print(f"✓ Logged {log_result['logged_count']} observations to {log_result['log_file']}")

        # Show accumulation stats (optional)
        stats = regime_logger.get_log_stats()
        if stats.get("total_observations", 0) > 0:
            print(f"  Total accumulated: {stats['total_observations']} observations")
    else:
        print(f"⚠ Logging failed: {log_result.get('error', 'unknown error')}")


if __name__ == "__main__":
    main()
