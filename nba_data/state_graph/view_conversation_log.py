#!/usr/bin/env python3
"""
대화 로그 뷰어

일자별 대화 로그를 읽기 쉬운 형태로 출력

사용법:
  python view_conversation_log.py                  # 오늘 로그
  python view_conversation_log.py 2025-12-25      # 특정 날짜
  python view_conversation_log.py --last 10       # 최근 10개 메시지
  python view_conversation_log.py --search "NBA"  # 검색
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class ConversationLogViewer:
    def __init__(self, log_dir: Path = None):
        if log_dir is None:
            log_dir = Path(__file__).parent / "logs"
        self.log_dir = log_dir

    def get_log_file(self, date: str = None) -> Path:
        """일자별 로그 파일 경로"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"conversation_{date}.jsonl"

    def read_log(self, date: str = None) -> List[Dict]:
        """로그 파일 읽기"""
        log_file = self.get_log_file(date)

        if not log_file.exists():
            print(f"⚠️  로그 파일 없음: {log_file}")
            return []

        messages = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON 파싱 오류: {e}")
                        continue

        return messages

    def format_message(self, msg: Dict, index: int = None) -> str:
        """메시지를 읽기 쉬운 형태로 포맷"""
        timestamp = msg.get('timestamp', 'N/A')
        msg_type = msg.get('type', 'unknown')
        content = msg.get('content', {})

        # 시간 포맷 (ISO → 읽기 쉬운 형태)
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = timestamp

        # 타입별 아이콘
        icon = "👤" if msg_type == "user_prompt" else "🤖"

        # 헤더
        header = f"\n{'='*80}\n"
        if index is not None:
            header += f"[{index+1}] "
        header += f"{icon} {msg_type.upper()} - {time_str}\n"
        header += f"{'='*80}\n"

        # 내용 (JSON pretty print)
        content_str = json.dumps(content, indent=2, ensure_ascii=False)

        return header + content_str

    def display_log(self, date: str = None, last_n: int = None, search: str = None):
        """로그 표시"""
        messages = self.read_log(date)

        if not messages:
            return

        print(f"\n📝 대화 로그: {self.get_log_file(date).name}")
        print(f"총 메시지: {len(messages)}개")

        # 검색 필터
        if search:
            messages = [
                msg for msg in messages
                if search.lower() in json.dumps(msg, ensure_ascii=False).lower()
            ]
            print(f"검색 결과: {len(messages)}개")

        # 최근 N개만
        if last_n:
            messages = messages[-last_n:]
            print(f"표시: 최근 {len(messages)}개")

        print()

        # 메시지 출력
        for i, msg in enumerate(messages):
            print(self.format_message(msg, i))

        print(f"\n{'='*80}")
        print(f"✅ 총 {len(messages)}개 메시지 표시")
        print(f"{'='*80}\n")

    def list_logs(self):
        """사용 가능한 로그 파일 목록"""
        if not self.log_dir.exists():
            print("⚠️  로그 디렉토리 없음")
            return

        log_files = sorted(self.log_dir.glob("conversation_*.jsonl"))

        if not log_files:
            print("⚠️  로그 파일 없음")
            return

        print("\n📂 사용 가능한 대화 로그:")
        print("="*60)

        for log_file in log_files:
            # 메시지 수 계산
            with open(log_file, 'r') as f:
                message_count = sum(1 for line in f if line.strip())

            # 파일 크기
            size_kb = log_file.stat().st_size / 1024

            # 날짜 추출
            date_str = log_file.stem.replace("conversation_", "")

            print(f"  {date_str:12s} - {message_count:4d}개 메시지 ({size_kb:6.1f} KB)")

        print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(description="대화 로그 뷰어")
    parser.add_argument("date", nargs='?', help="날짜 (YYYY-MM-DD, 기본: 오늘)")
    parser.add_argument("--last", type=int, help="최근 N개 메시지만 표시")
    parser.add_argument("--search", type=str, help="검색어")
    parser.add_argument("--list", action="store_true", help="사용 가능한 로그 파일 목록")

    args = parser.parse_args()

    viewer = ConversationLogViewer()

    if args.list:
        viewer.list_logs()
    else:
        viewer.display_log(
            date=args.date,
            last_n=args.last,
            search=args.search
        )

if __name__ == "__main__":
    main()
