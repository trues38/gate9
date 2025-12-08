import datetime

# Simplified Holiday Map (Placeholders - Expand with real dates or a library later)
# Format: "YYYY-MM-DD"
HOLIDAY_MAP = {
    "US": [
        "2000-01-01", "2000-01-17", "2000-02-21", "2000-05-29", "2000-07-04", "2000-09-04", "2000-11-23", "2000-12-25",
        # ... Add more as needed or load from external JSON
    ],
    "KR": [
        "2000-01-01", "2000-02-04", "2000-02-05", "2000-02-06", "2000-03-01", "2000-05-05", "2000-06-06", "2000-08-15", "2000-09-11", "2000-09-12", "2000-09-13", "2000-10-03", "2000-12-25"
    ],
    "JP": [
        "2000-01-01", "2000-01-10", "2000-02-11", "2000-03-20", "2000-04-29", "2000-05-03", "2000-05-04", "2000-05-05", "2000-07-17", "2000-09-15", "2000-09-23", "2000-10-09", "2000-11-03", "2000-11-23", "2000-12-23"
    ],
    "CN": [
        "2000-01-01", "2000-02-04", "2000-02-05", "2000-02-06", "2000-05-01", "2000-05-02", "2000-05-03", "2000-10-01", "2000-10-02", "2000-10-03"
    ]
}

def is_weekend(date_obj):
    # 5=Saturday, 6=Sunday
    return date_obj.weekday() >= 5

def is_holiday(date_str, country):
    if country not in HOLIDAY_MAP:
        return False
    return date_str in HOLIDAY_MAP[country]

def is_trading_day(date_str, country="GLOBAL"):
    """
    Determines if a date is a trading day for a specific country.
    For GLOBAL, it returns True if ANY major market is open (or simply checks weekend).
    """
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False

    # 1. Weekend Check
    if is_weekend(dt):
        return False
        
    # 2. Country Specific Holiday Check
    if country == "GLOBAL":
        # For Global, if US is open, we consider it a trading day?
        # Or if ALL are closed?
        # Let's say if US is closed, it's a "Global Holiday" for simplicity in this context,
        # OR we check if ALL are closed.
        # User requirement: "Global Mixed Report".
        # Let's check US for now as the anchor.
        if is_holiday(date_str, "US"):
            return False 
        return True
    else:
        return not is_holiday(date_str, country)

def get_no_session_json(date_str):
    """
    Returns the standardized No-Session JSON structure.
    """
    # Determine flags
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    weekend = is_weekend(dt)
    
    flags = {
        "US": not (weekend or is_holiday(date_str, "US")),
        "KR": not (weekend or is_holiday(date_str, "KR")),
        "JP": not (weekend or is_holiday(date_str, "JP")),
        "CN": not (weekend or is_holiday(date_str, "CN"))
    }
    
    # If it's a weekend, all are false
    if weekend:
        for k in flags: flags[k] = False
        
    return {
      "date": date_str,
      "is_trading_day": False,
      "headline_count": 0,
      "z_score_global": None,
      "delta_z": None,
      "arc_stage": None,
      "bias": None,
      "bridging": None,
      "chain": [],
      "summary": "Market closed / No trading session / Public holiday",
      "country_flags": flags
    }
