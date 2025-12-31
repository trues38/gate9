#!/usr/bin/env python3
"""
Box Score 자동 수집 API 서버

n8n에서 HTTP Request로 호출하여 Box Score 크롤링 및 Neo4j 임포트 실행
"""

from flask import Flask, jsonify
import subprocess
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = "/Users/js/g9/.venv/bin/python3"

@app.route('/health', methods=['GET'])
def health():
    """헬스 체크"""
    return jsonify({
        "status": "healthy",
        "service": "NBA Box Score API",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/boxscore/collect', methods=['POST', 'GET'])
def collect_boxscore():
    """
    Box Score 크롤링 및 Neo4j 임포트 실행

    Returns:
        JSON: {
            "status": "success" | "error",
            "message": "...",
            "crawl_output": "...",
            "import_output": "...",
            "timestamp": "..."
        }
    """
    try:
        # Step 1: Box Score 크롤링
        crawl_script = PROJECT_ROOT / "crawl_current_season_boxscores.py"
        crawl_result = subprocess.run(
            [VENV_PYTHON, str(crawl_script)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        crawl_success = crawl_result.returncode == 0
        crawl_output = crawl_result.stdout if crawl_success else crawl_result.stderr

        if not crawl_success:
            return jsonify({
                "status": "error",
                "message": "Box Score 크롤링 실패",
                "crawl_output": crawl_output,
                "timestamp": datetime.now().isoformat()
            }), 500

        # Step 2: Neo4j 임포트
        import_script = PROJECT_ROOT / "import_player_boxscores.py"
        import_result = subprocess.run(
            [VENV_PYTHON, str(import_script)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )

        import_success = import_result.returncode == 0
        import_output = import_result.stdout if import_success else import_result.stderr

        if not import_success:
            return jsonify({
                "status": "error",
                "message": "Neo4j 임포트 실패",
                "crawl_output": crawl_output,
                "import_output": import_output,
                "timestamp": datetime.now().isoformat()
            }), 500

        # 성공
        return jsonify({
            "status": "success",
            "message": "✅ Box Score 수집 및 임포트 완료",
            "crawl_output": crawl_output[-500:],  # 마지막 500자만
            "import_output": import_output[-500:],  # 마지막 500자만
            "timestamp": datetime.now().isoformat()
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "타임아웃: 스크립트 실행이 5분을 초과했습니다",
            "timestamp": datetime.now().isoformat()
        }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"예상치 못한 오류: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("="*80)
    print("🚀 NBA Box Score API 서버 시작")
    print("="*80)
    print(f"📍 URL: http://localhost:5001")
    print(f"🔗 Health: http://localhost:5001/health")
    print(f"🔗 Collect: http://localhost:5001/api/boxscore/collect")
    print("="*80)

    # Flask 서버 실행
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False
    )
