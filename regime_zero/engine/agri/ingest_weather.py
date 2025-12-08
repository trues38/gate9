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

# KMA API Key (Need to add to .env)
KMA_API_KEY = os.environ.get("KMA_API_KEY")

# Major Production Regions (Station IDs)
# 90: Sokcho (Highland Cabbage), 108: Seoul, 156: Gwangju (Jeonnam), 143: Daegu (Gyeongbuk)
STATIONS = {
    "Gangwon": "90", 
    "Jeonnam": "156",
    "Gyeongbuk": "143",
    "Jeju": "184"
}

def fetch_weather_daily():
    print(f"   ☁️ [Agri-Weather] Fetching KMA Data... [{datetime.now().strftime('%Y-%m-%d')}]")
    
    if not KMA_API_KEY:
        print("      ⚠️ KMA_API_KEY is missing in .env. Skipping.")
        return

    # Target Date: Yesterday (Since today's daily data isn't finished)
    target_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    for region, station_id in STATIONS.items():
        print(f"      📍 Fetching {region} (Stn: {station_id})...")
        
        # KMA API Endpoint (Daily Summary)
        url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
        params = {
            "serviceKey": KMA_API_KEY,
            "pageNo": "1",
            "numOfRows": "10",
            "dataType": "JSON",
            "dataCd": "ASOS",
            "dateCd": "DAY",
            "startDt": target_date,
            "endDt": target_date,
            "stnIds": station_id
        }
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            
            if not items:
                print("         ❌ No Data")
                continue
                
            item = items[0]
            
            # Prepare DB Row
            row = {
                "date": f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}",
                "region": region,
                "temp_avg": float(item.get('avgTa', 0) or 0),
                "rainfall": float(item.get('sumRn', 0) or 0),
                "sunshine": float(item.get('sumSsHr', 0) or 0),
                "humidity": float(item.get('avgRhm', 0) or 0),
                "wind": float(item.get('avgWs', 0) or 0),
                "weather_api_raw": item
            }
            
            # Upsert
            supabase.table("weather_daily").upsert(row).execute()
            print("         ✅ Saved")
            
        except Exception as e:
            print(f"         ❌ Error: {e}")

if __name__ == "__main__":
    fetch_weather_daily()
