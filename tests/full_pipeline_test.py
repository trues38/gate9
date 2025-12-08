# g9_orchestra/tests/full_pipeline_test.py

import json
from auto_sql_engine.auto_sql import run_auto_sql_engine

from orchestra.agent_orchestrator import (
    analyze_country_perspective,
    synthesize_meta_packet
)

from orchestra.agent_antigravity import generate_antigravity_report

TEST_TASK = "Test: Generate today's global macro analysis."

def print_section(title):
    print("\n" + "="*80)
    print(f"🚀 {title}")
    print("="*80 + "\n")

def run():
    print_section("1) STEP 1 — Auto-SQL Engine Running")
    sql_evidence = run_auto_sql_engine(TEST_TASK)
    print("SQL Evidence:\n", json.dumps(sql_evidence, indent=2))

    if not sql_evidence or "clean_evidence" not in sql_evidence:
        print("❌ SQL Evidence missing or invalid. Check DB connection or SQL runner.")
        print(f"Debug: {sql_evidence.keys() if sql_evidence else 'None'}")
        return

    print_section("2) STEP 2 — Persona Perspectives (US / CN / JP / KR)")
    perspectives = {}
    for country in ["US", "CN", "JP", "KR"]:
        perspectives[country] = analyze_country_perspective(
    sql_evidence,
    country,
    TEST_TASK
        )
        print(f"[{country} View] => {perspectives[country]}\n")

    if any("Taiwan" in x for x in perspectives.values()):
        print("⚠️ WARNING: 'Taiwan Loop' detected. Persona ignoring evidence.")
        print("→ Evidence not injected or Persona prompts not updated.\n")

    print_section("3) STEP 3 — Summit Moderator Synthesizing Meta-Packet")
    meta_packet = synthesize_meta_packet(perspectives, sql_evidence)
    print("Meta-Packet:\n", json.dumps(meta_packet, indent=2))

    print_section("4) STEP 4 — Antigravity Final Report")
    report = generate_antigravity_report(meta_packet, sql_evidence)
    print("Final Report:\n", report)

    print_section("5) SUMMARY")
    print("🎯 Pipeline Test Completed!\n")
    print("👉 If report still repeats Taiwan or looks generic:")
    print("- Auto-SQL is not injecting DB evidence.")
    print("- Persona prompts not referencing evidence key.")
    print("- Antigravity prompt missing evidence binding.\n")

if __name__ == "__main__":
    run()