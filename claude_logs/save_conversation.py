#!/usr/bin/env python3
"""
Claude Code 대화 로그 저장 스크립트
일자별로 대화를 JSON 형식으로 저장합니다.
"""

import os
import json
from datetime import datetime
import sys

def save_conversation_log(message, role="user"):
    """대화 메시지를 일자별 로그 파일에 추가"""

    # 로그 디렉토리
    log_dir = "/Users/js/g9/claude_logs"
    os.makedirs(log_dir, exist_ok=True)

    # 일자별 파일명
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"conversation_{today}.jsonl")

    # 로그 엔트리
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": message,
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown")
    }

    # JSONL 형식으로 추가
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ 로그 저장: {log_file}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        save_conversation_log(message, role="user")
    else:
        # stdin에서 읽기
        message = sys.stdin.read().strip()
        if message:
            save_conversation_log(message, role="assistant")
