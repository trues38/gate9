"""
LLM Tweet Processor

Uses MiMo-V2-Flash (free) via OpenRouter for:
- Event type classification
- Entity extraction (Player, Team, Referee, etc.)
- Importance scoring
- Deduplication logic

Philosophy:
"LLM is a data normalizer, not a decision maker"
→ Structure only, no judgment
"""

import requests
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class ProcessedEvent:
    """Structured event output from LLM"""
    event_type: str  # INJURY, LINEUP, REFEREE, TRADE, MARKET_NEWS, NOISE
    importance: float  # 0.0 - 1.0
    entities: Dict[str, Any]  # {player: "LeBron James", team: "LAL"}
    summary: str
    source_username: str
    timestamp: str  # ISO format
    raw_text: str
    tweet_id: str
    domain: str  # "nba" or "economy"
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None


class LLMProcessor:
    """
    LLM-based tweet processor using MiMo-V2-Flash (free)

    Key Features:
    - Batch processing (N tweets → N events)
    - Structured output (JSON)
    - Importance scoring
    - Entity extraction
    - Duplicate detection

    Cost: $0.00 (free tier via OpenRouter)
    """

    def __init__(self, openrouter_key: str = None):
        self.openrouter_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        self.model = "xiaomi/mimo-v2-flash:free"  # Free tier
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        if not self.openrouter_key:
            logger.warning("OPENROUTER_API_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        logger.info(f"LLMProcessor initialized (model={self.model}, mock={self.mock_mode})")

    def process_tweets_batch(
        self,
        tweets: List[Dict[str, Any]],
        domain: str = "nba"
    ) -> List[ProcessedEvent]:
        """
        Process a batch of raw tweets into structured events

        Args:
            tweets: List of raw tweet dicts
            domain: "nba" or "economy"

        Returns:
            List of ProcessedEvent objects
        """
        if not tweets:
            return []

        if self.mock_mode:
            return self._mock_process(tweets, domain)

        try:
            # Build prompt
            prompt = self._build_prompt(tweets, domain)

            # Call LLM
            response = self._call_llm(prompt)

            # Parse response
            events = self._parse_llm_response(response, tweets, domain)

            logger.info(f"LLM processed {len(tweets)} tweets → {len(events)} events")
            return events

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return []

    def _build_prompt(self, tweets: List[Dict[str, Any]], domain: str) -> str:
        """Build LLM prompt for batch processing"""

        if domain == "nba":
            event_types = "INJURY, LINEUP, REFEREE, QUESTIONABLE, RESTRICTION, EJECTION, TRADE, NOISE"
            entities = "player, team, game, referee, status"
        else:  # economy
            event_types = "MARKET_NEWS, POLICY_CHANGE, MACRO_DATA, SENTIMENT, ANALYSIS, NOISE"
            entities = "asset, sector, indicator, central_bank, policy"

        tweets_json = json.dumps([
            {
                "id": t.get("tweet_id"),
                "username": t.get("username"),
                "text": t.get("text"),
                "created_at": t.get("created_at")
            }
            for t in tweets
        ], indent=2)

        prompt = f"""You are a data normalizer for {domain.upper()} information.

TASK: Convert raw tweets into structured events.

EVENT TYPES: {event_types}
ENTITIES: {entities}

RULES:
1. Classify each tweet by event_type
2. Extract relevant entities
3. Score importance (0.0 = noise, 1.0 = critical)
4. Write 1-sentence summary
5. Mark NOISE if irrelevant (analysis, jokes, ads)

INPUT TWEETS:
{tweets_json}

OUTPUT FORMAT (JSON array):
[
  {{
    "tweet_id": "...",
    "event_type": "INJURY",
    "importance": 0.87,
    "entities": {{"player": "LeBron James", "team": "LAL", "status": "OUT"}},
    "summary": "LeBron James ruled OUT with ankle injury"
  }},
  ...
]

IMPORTANT:
- ONLY output valid JSON array
- NO explanations, NO markdown
- Include ALL input tweets in output
"""

        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Low temp for consistency
            "max_tokens": 2000
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error {response.status_code}: {response.text}")
            return ""

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _parse_llm_response(
        self,
        response: str,
        original_tweets: List[Dict[str, Any]],
        domain: str
    ) -> List[ProcessedEvent]:
        """Parse LLM JSON response into ProcessedEvent objects"""
        try:
            # Extract JSON from response (in case LLM adds markdown)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            events_data = json.loads(response)

            events = []
            for event_data in events_data:
                # Skip NOISE events
                if event_data.get("event_type") == "NOISE":
                    continue

                # Find original tweet
                tweet_id = event_data.get("tweet_id")
                original = next((t for t in original_tweets if t.get("tweet_id") == tweet_id), None)
                if not original:
                    continue

                event = ProcessedEvent(
                    event_type=event_data.get("event_type", "UNKNOWN"),
                    importance=float(event_data.get("importance", 0.5)),
                    entities=event_data.get("entities", {}),
                    summary=event_data.get("summary", ""),
                    source_username=original.get("username", ""),
                    timestamp=original.get("created_at", datetime.now().isoformat()),
                    raw_text=original.get("text", ""),
                    tweet_id=tweet_id,
                    domain=domain
                )

                events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []

    def _mock_process(
        self,
        tweets: List[Dict[str, Any]],
        domain: str
    ) -> List[ProcessedEvent]:
        """Mock processing for testing"""
        logger.info(f"[MOCK] Processing {len(tweets)} tweets")

        events = []
        for tweet in tweets:
            text = tweet.get("text", "").lower()

            # Simple keyword-based classification
            if domain == "nba":
                if any(word in text for word in ["out", "injury", "injured"]):
                    event_type = "INJURY"
                    importance = 0.8
                elif any(word in text for word in ["starting", "lineup"]):
                    event_type = "LINEUP"
                    importance = 0.7
                elif any(word in text for word in ["referee", "crew chief"]):
                    event_type = "REFEREE"
                    importance = 0.6
                else:
                    event_type = "NOISE"
                    importance = 0.2
            else:  # economy
                if any(word in text for word in ["fed", "rate", "policy"]):
                    event_type = "POLICY_CHANGE"
                    importance = 0.9
                elif any(word in text for word in ["market", "stocks", "rally"]):
                    event_type = "MARKET_NEWS"
                    importance = 0.7
                else:
                    event_type = "NOISE"
                    importance = 0.3

            if event_type == "NOISE":
                continue

            event = ProcessedEvent(
                event_type=event_type,
                importance=importance,
                entities={},
                summary=tweet.get("text", "")[:100],
                source_username=tweet.get("username", ""),
                timestamp=tweet.get("created_at", datetime.now().isoformat()),
                raw_text=tweet.get("text", ""),
                tweet_id=tweet.get("tweet_id", ""),
                domain=domain
            )

            events.append(event)

        logger.info(f"[MOCK] Processed {len(tweets)} → {len(events)} events")
        return events

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            "model": self.model,
            "mock_mode": self.mock_mode,
            "provider": "openrouter",
            "cost": "$0.00 (free tier)"
        }
