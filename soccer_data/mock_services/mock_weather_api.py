import json
import random

def get_mock_soccer_weather(lat, lon):
    """
    Returns mock weather data matching 'OpenWeatherMap' format.
    """
    scenarios = [
        {"main": "Rain", "description": "moderate rain", "temp": 12.5, "wind_speed": 5.2},
        {"main": "Clear", "description": "clear sky", "temp": 18.0, "wind_speed": 1.5},
        {"main": "Clouds", "description": "overcast clouds", "temp": 14.2, "wind_speed": 3.0},
        {"main": "Windy", "description": "high winds", "temp": 10.1, "wind_speed": 10.5}
    ]
    
    scenario = random.choice(scenarios)
    
    mock_data = {
        "coord": {"lat": lat, "lon": lon},
        "weather": [{"main": scenario["main"], "description": scenario["description"]}],
        "main": {"temp": scenario["temp"], "humidity": 70},
        "wind": {"speed": scenario["wind_speed"]}
    }
    return mock_data

if __name__ == "__main__":
    weather = get_mock_soccer_weather(53.48, -2.24) # Manchester
    print(json.dumps(weather, indent=4))
