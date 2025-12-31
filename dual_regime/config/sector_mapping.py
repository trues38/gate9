#!/usr/bin/env python3
"""
Sector Mapping Configuration
=============================
Defines 17-sector taxonomy with ETF + US stocks + KR stocks mapping
"""

SECTOR_TAXONOMY = {
    "SEMICONDUCTORS": {
        "etf": "SOXX",
        "us_stocks": ["NVDA", "AMD", "INTC", "TSM", "ASML", "AVGO", "QCOM", "MU", "AMAT", "LRCX", "KLAC"],
        "kr_stocks": ["005930.KS", "000660.KS"]  # Samsung Electronics, SK Hynix
    },
    "TECH_SOFTWARE": {
        "etf": "XLK",
        "us_stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
        "kr_stocks": ["035720.KS", "035420.KS"]  # Kakao, Naver
    },
    "SOFTWARE_CLOUD": {
        "etf": "IGV",  # iShares Expanded Tech-Software Sector ETF
        "us_stocks": ["CRM", "ADBE", "ORCL", "NOW", "SNOW", "PLTR", "PANW"],
        "kr_stocks": []
    },
    "BIOTECH": {
        "etf": "XBI",
        "us_stocks": ["LLY", "PFE", "MRNA", "ABBV"],
        "kr_stocks": ["207940.KS", "068270.KS"]  # Samsung Biologics, Celltrion
    },
    "HEALTHCARE": {
        "etf": "XLV",
        "us_stocks": ["UNH", "JNJ", "TMO", "ISRG"],
        "kr_stocks": []
    },
    "BATTERY_EV": {
        "etf": "LIT",
        "us_stocks": ["TSLA"],
        "kr_stocks": ["373220.KS", "006400.KS", "051910.KS"]  # LG Energy Solution, Samsung SDI, LG Chem
    },
    "CLEAN_ENERGY": {
        "etf": "TAN",
        "us_stocks": ["TSLA", "RIVN", "LCID", "NIO", "XPEV", "ENPH", "FSLR"],
        "kr_stocks": []
    },
    "AUTOMOTIVE": {
        "etf": "CARZ",
        "us_stocks": ["TSLA", "RIVN"],
        "kr_stocks": ["005380.KS", "000270.KS"]  # Hyundai Motor, Kia
    },
    "SHIPBUILDING": {
        "etf": None,  # No specific ETF
        "us_stocks": [],
        "kr_stocks": ["010140.KS", "009540.KS", "042660.KS"]  # Samsung Heavy Industries, HD Hyundai Heavy Industries, Hanwha Ocean
    },
    "INDUSTRIAL": {
        "etf": "XLI",
        "us_stocks": ["BA", "LMT", "RTX", "CAT", "DE", "HON"],
        "kr_stocks": ["012450.KS", "047810.KS"]  # Hanwha Aerospace, Korea Aerospace Industries
    },
    "FINANCE": {
        "etf": "XLF",
        "us_stocks": ["JPM", "BAC", "GS", "MS", "BLK", "C"],
        "kr_stocks": ["105560.KS", "055550.KS"]  # KB Financial, Shinhan Financial
    },
    "FINTECH": {
        "etf": None,
        "us_stocks": ["V", "MA", "PYPL", "SQ", "COIN"],
        "kr_stocks": []
    },
    "CONSUMER_DISCRETIONARY": {
        "etf": "XLY",
        "us_stocks": ["AMZN", "TSLA", "NKE", "SBUX", "MCD", "DIS"],
        "kr_stocks": ["352820.KS", "041510.KS"]  # Hybe, SM Entertainment
    },
    "CONSUMER_STAPLES": {
        "etf": "XLP",
        "us_stocks": [],
        "kr_stocks": []
    },
    "ENERGY": {
        "etf": "XLE",
        "us_stocks": ["XOM", "CVX", "COP"],
        "kr_stocks": []
    },
    "MATERIALS": {
        "etf": "XLB",
        "us_stocks": [],
        "kr_stocks": ["005490.KS"]  # POSCO Holdings
    },
    "ECOMMERCE": {
        "etf": None,
        "us_stocks": ["AMZN", "SHOP", "BABA", "JD"],
        "kr_stocks": ["035720.KS", "035420.KS"]  # Kakao, Naver
    }
}

# Flatten to ticker lists
ALL_ETFS = [s["etf"] for s in SECTOR_TAXONOMY.values() if s["etf"] is not None]
ALL_US_STOCKS = list(set([ticker for s in SECTOR_TAXONOMY.values() for ticker in s["us_stocks"]]))
ALL_KR_STOCKS = list(set([ticker for s in SECTOR_TAXONOMY.values() for ticker in s["kr_stocks"]]))

# Reverse mapping: ticker -> sector
TICKER_TO_SECTOR = {}
for sector, data in SECTOR_TAXONOMY.items():
    if data["etf"]:
        TICKER_TO_SECTOR[data["etf"]] = sector
    for ticker in data["us_stocks"]:
        TICKER_TO_SECTOR[ticker] = sector
    for ticker in data["kr_stocks"]:
        TICKER_TO_SECTOR[ticker] = sector

# Summary stats
print(f"Sector Taxonomy Summary:")
print(f"  Total Sectors: {len(SECTOR_TAXONOMY)}")
print(f"  Total ETFs: {len(ALL_ETFS)}")
print(f"  Total US Stocks: {len(ALL_US_STOCKS)}")
print(f"  Total KR Stocks: {len(ALL_KR_STOCKS)}")
print(f"  Total Tickers: {len(ALL_ETFS) + len(ALL_US_STOCKS) + len(ALL_KR_STOCKS)}")
