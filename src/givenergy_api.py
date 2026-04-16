import requests
import logging
import time
from datetime import datetime, timedelta
from config.settings import GIVENERGY_API_URI, GIVENERGY_API_KEY, GIVENERGY_DEVICE_ID

logger = logging.getLogger(__name__)

def get_solar_generation(target_date_from, target_date_to):

    url = f"{GIVENERGY_API_URI}/v1/inverter/{GIVENERGY_DEVICE_ID}/energy-flows"
    all_results = []
    
    # Convert date strings to datetime objects if they're strings
    if isinstance(target_date_from, str):
        current_date = datetime.strptime(target_date_from, "%Y-%m-%d").date()
    else:
        current_date = target_date_from
    
    if isinstance(target_date_to, str):
        end_date = datetime.strptime(target_date_to, "%Y-%m-%d").date()
    else:
        end_date = target_date_to
    
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {GIVENERGY_API_KEY}",
        "content-type": "application/json"
    }
    
    # Loop through each day from target_date_from to target_date_to
    while current_date <= end_date:
        start_time = current_date.strftime("%Y-%m-%d")
        end_time = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "start_time": start_time,
            "end_time": end_time,
            "grouping": 0,
            "types": [0]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data and "data" in data:
                # Transform the nested object structure to array of objects
                for key in sorted(data["data"].keys(), key=lambda x: int(x)):
                    item = data["data"][key]
                    all_results.append({
                        "start_time": item.get("start_time"),
                        "end_time": item.get("end_time"),
                        "data": item.get("data")
                    })
            
            logger.info(f"Successfully fetched data for {start_time}")
            time.sleep(1)  # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data for {start_time}: {str(e)}")
        
        current_date += timedelta(days=1)
    
    return all_results
