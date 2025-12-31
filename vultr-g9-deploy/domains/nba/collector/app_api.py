"""
G9 NBA Collector API - Flask wrapper for the pipeline

Provides REST API endpoints for the data collection pipeline
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from main_pipeline import G9Pipeline
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize pipeline
pipeline = G9Pipeline()

logger.info("=" * 60)
logger.info("G9 NBA Collector API Started")
logger.info("=" * 60)


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "G9 NBA Collector (Free Pipeline)",
        "version": "3.0.0"
    })


@app.route('/collect/nba', methods=['POST'])
def collect_nba():
    """Run NBA collection"""
    try:
        data = request.json or {}
        game_times = data.get('game_times', [])

        # Convert ISO strings to datetime
        game_times_parsed = []
        for gt in game_times:
            try:
                game_times_parsed.append(datetime.fromisoformat(gt))
            except:
                pass

        result = pipeline.run_nba_collection(game_times_parsed)
        return jsonify(result)

    except Exception as e:
        logger.error(f"NBA collection failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/collect/economy', methods=['POST'])
def collect_economy():
    """Run Economy collection"""
    try:
        result = pipeline.run_economy_collection()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Economy collection failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/process/llm', methods=['POST'])
def process_llm():
    """Process unprocessed tweets with LLM"""
    try:
        data = request.json or {}
        domain = data.get('domain', 'nba')
        batch_size = data.get('batch_size', 50)

        result = pipeline.run_llm_processing(domain=domain, batch_size=batch_size)
        return jsonify(result)

    except Exception as e:
        logger.error(f"LLM processing failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/collect/odds', methods=['POST'])
def collect_odds():
    """
    Collect NBA odds

    Body:
        tier: "tier1" (all games) or "tier2" (top games)
        snapshot_type: "open" (T-24h), "mid" (T-3h), or "close" (T-1h)
    """
    try:
        data = request.json or {}
        tier = data.get('tier', 'tier1')
        snapshot_type = data.get('snapshot_type', 'close')

        result = pipeline.run_odds_collection(tier=tier, snapshot_type=snapshot_type)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Odds collection failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/odds/latest', methods=['GET'])
def get_latest_odds():
    """Get latest odds snapshots"""
    try:
        game_id = request.args.get('game_id', None)
        snapshot_type = request.args.get('snapshot_type', None)

        odds = pipeline.neo4j.get_latest_odds(
            game_id=game_id,
            snapshot_type=snapshot_type
        )

        return jsonify({
            "odds": odds,
            "count": len(odds)
        })

    except Exception as e:
        logger.error(f"Failed to get odds: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/budget/status', methods=['GET'])
def budget_status():
    """Get API budget status"""
    try:
        status = pipeline.scheduler.get_budget_status()
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/storage/stats', methods=['GET'])
def storage_stats():
    """Get raw storage statistics"""
    try:
        stats = pipeline.raw_storage.get_stats()
        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/tweets/recent', methods=['GET'])
def recent_tweets():
    """Get recent tweets for inspection"""
    try:
        domain = request.args.get('domain', None)
        limit = int(request.args.get('limit', 10))
        include_processed = request.args.get('include_processed', 'true').lower() == 'true'

        tweets = pipeline.raw_storage.get_recent_tweets(
            domain=domain,
            limit=limit,
            include_processed=include_processed
        )
        return jsonify({
            "tweets": tweets,
            "count": len(tweets)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/status', methods=['GET'])
def full_status():
    """Get full system status"""
    try:
        status = pipeline.get_status()
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001, debug=False)
