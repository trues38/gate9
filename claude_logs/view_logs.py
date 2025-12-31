#!/usr/bin/env python3
"""
Claude Code 세션 로그 뷰어
저장된 로그를 읽기 쉽게 표시합니다.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/Users/js/g9/claude_logs")

def view_today_log():
    """오늘의 로그 표시"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"conversation_{today}.jsonl"

    if not log_file.exists():
        print(f"❌ 오늘의 로그가 없습니다: {log_file}")
        return

    print("=" * 80)
    print(f"세션 로그: {today}")
    print("=" * 80)

    with open(log_file, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    for i, entry in enumerate(entries, 1):
        timestamp = entry['timestamp'].split('T')[1][:5]  # HH:MM만
        entry_type = entry['type'].upper()
        content = entry['content']

        icon = {
            'MILESTONE': '🎯',
            'DECISION': '🤔',
            'ERROR': '⚠️',
            'SUMMARY': '📋'
        }.get(entry_type, '•')

        print(f"\n{i}. [{timestamp}] {icon} {entry_type}")
        print(f"   {content}")

        if 'details' in entry and entry['details']:
            print(f"   상세:")
            for key, value in list(entry['details'].items())[:3]:
                if isinstance(value, (int, float, str)):
                    print(f"     - {key}: {value}")

def view_summary():
    """오늘의 요약 표시"""
    today = datetime.now().strftime("%Y-%m-%d")
    summary_file = LOG_DIR / f"session_summary_{today}.md"

    if not summary_file.exists():
        print(f"❌ 오늘의 요약이 없습니다: {summary_file}")
        return

    with open(summary_file, "r", encoding="utf-8") as f:
        content = f.read()

    print(content)

def list_logs():
    """모든 로그 파일 목록"""
    print("\n사용 가능한 로그 파일:")
    print("-" * 80)

    jsonl_files = sorted(LOG_DIR.glob("conversation_*.jsonl"), reverse=True)
    md_files = sorted(LOG_DIR.glob("session_summary_*.md"), reverse=True)

    if not jsonl_files:
        print("로그 파일이 없습니다.")
        return

    for log_file in jsonl_files[:10]:  # 최근 10개만
        date = log_file.stem.replace("conversation_", "")

        # 항목 수 계산
        with open(log_file, "r") as f:
            count = sum(1 for _ in f)

        summary_exists = (LOG_DIR / f"session_summary_{date}.md").exists()
        summary_mark = "📄" if summary_exists else "  "

        print(f"  {date}  {summary_mark}  {count}개 이벤트  {log_file.name}")

def resume_session():
    """세션 복원을 위한 최근 작업 표시"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"conversation_{today}.jsonl"

    if not log_file.exists():
        print(f"❌ 오늘의 로그가 없습니다.")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    print("=" * 80)
    print("세션 복원: 최근 작업")
    print("=" * 80)

    # 최근 5개 항목
    recent = entries[-5:]

    for entry in recent:
        timestamp = entry['timestamp'].split('T')[1][:5]
        print(f"\n[{timestamp}] {entry['type'].upper()}")
        print(f"  {entry['content']}")

    # 마지막이 summary이면 다음 단계 표시
    if recent[-1]['type'] == 'summary':
        next_steps = recent[-1].get('details', {}).get('next_steps', [])
        if next_steps:
            print("\n" + "=" * 80)
            print("다음 작업 단계:")
            print("=" * 80)
            for i, step in enumerate(next_steps, 1):
                print(f"{i}. {step}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "summary":
            view_summary()
        elif command == "list":
            list_logs()
        elif command == "resume":
            resume_session()
        else:
            print(f"알 수 없는 명령: {command}")
            print("사용법: python view_logs.py [today|summary|list|resume]")
    else:
        # 기본: 오늘 로그 표시
        view_today_log()
