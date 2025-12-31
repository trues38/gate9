import json
import random

def get_mock_soccer_injuries(team_name):
    """
    Returns mock injury data simulating 'PhysioRoom' or 'InjuryReport' data.
    """
    types = ["Hamstring", "Ankle Sprain", "Knee Ligament", "Muscle Strain", "Flu"]
    severities = ["Low", "Moderate", "High"]
    
    # Mocking a list of injured players for the team
    num_injuries = random.randint(0, 5)
    injuries = []
    
    for i in range(num_injuries):
        injuries.append({
            "player": f"Player_{random.randint(1, 25)}",
            "type": random.choice(types),
            "severity": random.choice(severities),
            "return_date": f"2025-01-{random.randint(5, 30)}"
        })
    
    return {"team": team_name, "injuries": injuries}

if __name__ == "__main__":
    injuries = get_mock_soccer_injuries("Man United")
    print(json.dumps(injuries, indent=4))
