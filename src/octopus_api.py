import requests
import logging
from config.settings import OCTOPUS_API_URI, OCTOPUS_API_KEY, IMPORT_MPAN, EXPORT_MPAN, METER_SERIAL

logger = logging.getLogger(__name__)

def get_params(target_date_from, target_date_to):
    return {
        "period_from": target_date_from,
        "period_to": target_date_to,
        "order_by": "period"
    }

def get_import_consumption(target_date_from, target_date_to):
    params = get_params(target_date_from, target_date_to)
    return get_consumption(IMPORT_MPAN, METER_SERIAL, params)

def get_export_consumption(target_date_from, target_date_to):
    params = get_params(target_date_from, target_date_to)
    return get_consumption(EXPORT_MPAN, METER_SERIAL, params)

def get_consumption(mpan, serial, params):
    """
    Fetch consumption data with pagination support.
    Retrieves all pages and aggregates results into a single list.
    """
    if not OCTOPUS_API_URI or not OCTOPUS_API_KEY or not mpan or not serial:
        logger.warning(
            "Missing Octopus API configuration: "
            f"OCTOPUS_API_URI={OCTOPUS_API_URI!r}, OCTOPUS_API_KEY={'***' if OCTOPUS_API_KEY else None}, "
            f"mpan={mpan!r}, serial={serial!r}"
        )
        return []

    url = f"{OCTOPUS_API_URI}/v1/electricity-meter-points/{mpan}/meters/{serial}/consumption/"
    all_results = []
    page = 1
    
    while url:
        response = requests.get(url, auth=(OCTOPUS_API_KEY, ""), params=params if page == 1 else None)
        response.raise_for_status()
        
        data = response.json()
        all_results.extend(data.get("results", []) or [])
        
        # Get the next page URL
        url = data.get("next")
        page += 1
    
    if not all_results:
        logger.warning(
            "Retrieved zero consumption records from Octopus. "
            "Check the date range, MPAN/serial values, and whether the account has data for this period."
        )
    else:
        logger.info(f"Retrieved total of {len(all_results)} consumption records")

    return all_results
