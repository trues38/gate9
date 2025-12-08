import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables
load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# KAMIS (Korea Agricultural Marketing Information Service) API Key
KAMIS_API_KEY = os.environ.get("KAMIS_API_KEY")
KAMIS_CERT_KEY = os.environ.get("KAMIS_CERT_KEY") # Sometimes needed

# Crop Codes (KAMIS Standard)
# 111: Rice, 211: Cabbage, 212: Radish, 223: Garlic, 224: Onion, 232: Pepper
CROPS = {
    "onion": {"category_code": "200", "item_code": "224", "kind_code": "00"},
    "cabbage": {"category_code": "200", "item_code": "211", "kind_code": "01"}, # Highland Cabbage
    "radish": {"category_code": "200", "item_code": "212", "kind_code": "00"},
    "garlic": {"category_code": "200", "item_code": "223", "kind_code": "00"},
    "potato": {"category_code": "100", "item_code": "152", "kind_code": "01"} # Sumi Potato
}

def fetch_market_prices():
    print(f"   💰 [Agri-Market] Fetching KAMIS Price Data... [{datetime.now().strftime('%Y-%m-%d')}]")
    
    if not KAMIS_API_KEY:
        print("      ⚠️ KAMIS_API_KEY is missing in .env. Skipping.")
        return

    # Target Date: Today
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for crop_name, codes in CROPS.items():
        print(f"      🥬 Checking {crop_name}...")
        
        # KAMIS Daily Price API URL (Example structure)
        url = "http://www.kamis.or.kr/service/price/xml.do"
        params = {
            "action": "dailyPriceByCategoryList",
            "p_cert_key": KAMIS_API_KEY,
            "p_cert_id": KAMIS_CERT_KEY,
            "p_returntype": "json",
            "p_product_cls_code": "02", # 01: Retail, 02: Wholesale
            "p_item_category_code": codes['category_code'],
            "p_country_code": "1101", # Seoul (Garak)
            "p_regday": today_str
        }
        
        try:
            # Mocking response for skeleton
            # res = requests.get(url, params=params)
            # data = res.json()
            
            # Placeholder Logic
            print("         ⚠️ API Key needed to fetch real data.")
            
            # Example Data Structure for DB
            # row = {
            #     "date": today_str,
            #     "crop": crop_name,
            #     "wholesale_price": 1500.0,
            #     "retail_price": 0.0,
            #     "origin_market": "Garak",
            #     "price_raw": {}
            # }
            # supabase.table("crop_price_daily").upsert(row).execute()
            
        except Exception as e:
            print(f"         ❌ Error: {e}")

if __name__ == "__main__":
    fetch_market_prices()
