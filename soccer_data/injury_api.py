#!/usr/bin/env python3
"""
Injury Data Collection API
n8n에서 호출할 수 있는 Flask API 서버
"""

from flask import Flask, jsonify, request
from injury_scraper import InjuryScraper
import json
import os
from datetime import datetime

app = Flask(__name__)
scraper = InjuryScraper()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "soccer-injury-api",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/collect/injuries', methods=['POST'])
def collect_injuries():
    """
    부상 데이터 수집 엔드포인트

    Request Body (optional):
    {
        "leagues": ["EPL", "La_liga"],  // 특정 리그만 수집
        "save": true                     // 파일 저장 여부
    }
    """
    try:
        data = request.get_json() or {}
        leagues_filter = data.get('leagues', None)
        save_file = data.get('save', True)

        print(f"\n📥 Injury collection request received")
        print(f"   Leagues: {leagues_filter or 'ALL'}")
        print(f"   Save: {save_file}")

        # 스크래핑 실행
        if leagues_filter:
            # 특정 리그만
            all_injuries = []
            for league in leagues_filter:
                if league in scraper.leagues:
                    injuries = scraper.scrape_league_injuries(league, scraper.leagues[league])
                    all_injuries.extend(injuries)
        else:
            # 모든 리그
            all_injuries = scraper.scrape_all_leagues()

        # 파일 저장
        if save_file and all_injuries:
            scraper.save_to_file(all_injuries)

        # 요약 통계
        summary = scraper.get_summary(all_injuries)

        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "injuries": all_injuries,
                "summary": summary
            }
        }), 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/injuries/latest', methods=['GET'])
def get_latest_injuries():
    """저장된 최신 부상 데이터 조회"""
    try:
        filepath = "processed/injury_data.json"

        if not os.path.exists(filepath):
            return jsonify({
                "status": "error",
                "message": "No injury data found. Run collection first."
            }), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            injuries = json.load(f)

        # 필터링 옵션
        league = request.args.get('league')
        status = request.args.get('status')
        impact = request.args.get('impact')

        filtered = injuries

        if league:
            filtered = [i for i in filtered if i['league'] == league]
        if status:
            filtered = [i for i in filtered if i['status'] == status]
        if impact:
            filtered = [i for i in filtered if i['impact'] == impact]

        summary = scraper.get_summary(filtered)

        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "count": len(filtered),
            "data": filtered,
            "summary": summary
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/injuries/critical', methods=['GET'])
def get_critical_injuries():
    """Critical 영향도 부상만 조회"""
    try:
        filepath = "processed/injury_data.json"

        if not os.path.exists(filepath):
            return jsonify({
                "status": "error",
                "message": "No injury data found"
            }), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            injuries = json.load(f)

        critical = [i for i in injuries if i['impact'] == 'CRITICAL']

        return jsonify({
            "status": "success",
            "count": len(critical),
            "data": critical
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("⚽ Soccer Injury API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET  /health              - Health check")
    print("  POST /collect/injuries    - Collect injury data")
    print("  GET  /injuries/latest     - Get latest injuries")
    print("  GET  /injuries/critical   - Get critical injuries only")
    print("\n" + "=" * 60)

    # Development server (VPS에서는 Gunicorn 사용)
    app.run(host='0.0.0.0', port=8002, debug=False)
