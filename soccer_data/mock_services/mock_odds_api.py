import json
from datetime import datetime
import random

def get_mock_soccer_odds(sport_key="soccer_epl"):
    """
    Returns mock odds data matching 'The Odds API' format.
    """
    teams = ["Man United", "Liverpool", "Man City", "Arsenal", "Chelsea", "Tottenham"]
    random.shuffle(teams)
    
    match_id = "mock_" + str(random.randint(1000, 9999))
    
    mock_data = [
        {
            "id": match_id,
            "sport_key": sport_key,
            "sport_title": "Soccer",
            "commence_time": datetime.now().isoformat() + "Z",
            "home_team": teams[0],
            "away_team": teams[1],
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "last_update": datetime.now().isoformat() + "Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": teams[0], "price": 2.10},
                                {"name": teams[1], "price": 3.40},
                                {"name": "Draw", "price": 3.20}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    return mock_data

if __name__ == "__main__":
    odds = get_mock_soccer_odds()
    print(json.dumps(odds, indent=4))
