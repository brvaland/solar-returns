from config.settings import (
    PEAK_START_HOUR, PEAK_END_HOUR
)
from datetime import datetime
from zoneinfo import ZoneInfo

def is_peak_hour(interval_start_str):
    """
    Determine if a given interval is during peak hours in UK timezone.
    Peak hours: 15:00 - 18:00 UK time (handles BST/GMT)
    """
    # Parse the ISO timestamp
    dt = datetime.fromisoformat(interval_start_str.replace('Z', '+00:00'))
    
    # Convert to UK timezone (Europe/London)
    uk_tz = ZoneInfo("Europe/London")
    dt_uk = dt.astimezone(uk_tz)
    
    hour = dt_uk.hour
    return PEAK_START_HOUR <= hour < PEAK_END_HOUR

def get_rate(is_peak, rate_type, import_peak_rate, import_offpeak_rate, export_peak_rate, export_offpeak_rate):
    """
    Get the appropriate rate based on peak/off-peak and type (import/export).
    """
    if rate_type == "import":
        return import_peak_rate if is_peak else import_offpeak_rate
    elif rate_type == "export":
        return export_peak_rate if is_peak else export_offpeak_rate
    else:
        raise ValueError(f"Invalid rate_type: {rate_type}")

def calculate_return_for_interval(import_consumption, export_consumption, 
                                  interval_start, pv_to_home_kwh=0, grid_to_battery_kwh=0,
                                  import_peak_rate=None, import_offpeak_rate=None, 
                                  export_peak_rate=None, export_offpeak_rate=None):
    """
    Calculate return for a single half-hour interval with peak/off-peak rates.
    
    Args:
        import_consumption: kWh imported in this interval
        export_consumption: kWh exported in this interval
        interval_start: ISO format timestamp string
        pv_to_home_kwh: kWh of PV consumed in the home during this interval
        grid_to_battery_kwh: kWh sent from grid to battery in this interval
        import_peak_rate: Peak import rate (optional, uses settings default)
        import_offpeak_rate: Off-peak import rate (optional, uses settings default)
        export_peak_rate: Peak export rate (optional, uses settings default)
        export_offpeak_rate: Off-peak export rate (optional, uses settings default)
    
    Returns:
        Dictionary with calculated values for this interval
    """
    # Import defaults from settings if not provided
    if import_peak_rate is None or import_offpeak_rate is None or export_peak_rate is None or export_offpeak_rate is None:
        from config.settings import IMPORT_PEAK_RATE, IMPORT_OFFPEAK_RATE, EXPORT_PEAK_RATE, EXPORT_OFFPEAK_RATE
        import_peak_rate = import_peak_rate or IMPORT_PEAK_RATE
        import_offpeak_rate = import_offpeak_rate or IMPORT_OFFPEAK_RATE
        export_peak_rate = export_peak_rate or EXPORT_PEAK_RATE
        export_offpeak_rate = export_offpeak_rate or EXPORT_OFFPEAK_RATE
    
    peak = is_peak_hour(interval_start)
    
    import_rate = get_rate(peak, "import", import_peak_rate, import_offpeak_rate, export_peak_rate, export_offpeak_rate)
    export_rate = get_rate(peak, "export", import_peak_rate, import_offpeak_rate, export_peak_rate, export_offpeak_rate)
    
    pv_to_home_savings = pv_to_home_kwh * import_rate
    export_income = export_consumption * export_rate
    import_cost = import_consumption * import_rate
    
    return {
        "import_kwh": import_consumption,
        "import_cost": import_cost,
        "export_kwh": export_consumption,
        "export_income": export_income,
        "pv_to_home_kwh": pv_to_home_kwh,
        "grid_to_battery_kwh": grid_to_battery_kwh,
        "is_peak": peak
    }

def aggregate_by_peak_offpeak(all_results):
    """
    Aggregate half-hourly results by peak and off-peak periods.
    
    Args:
        all_results: List of tuples (month, results_dict)
    
    Returns:
        Dictionary with aggregated results for 'peak' and 'off-peak'
    """
    aggregated = {
        "peak": {
            "import_kwh": 0,
            "import_cost": 0,
            "export_kwh": 0,
            "export_income": 0,
            "pv_to_home_kwh": 0,
            "grid_to_battery_kwh": 0,
            "intervals": 0
        },
        "off-peak": {
            "import_kwh": 0,
            "import_cost": 0,
            "export_kwh": 0,
            "export_income": 0,
            "pv_to_home_kwh": 0,
            "grid_to_battery_kwh": 0,
            "intervals": 0
        }
    }
    
    for _, results in all_results:
        period = "peak" if results["is_peak"] else "off-peak"
        
        aggregated[period]["import_kwh"] += results["import_kwh"]
        aggregated[period]["import_cost"] += results["import_cost"]
        aggregated[period]["export_kwh"] += results["export_kwh"]
        aggregated[period]["export_income"] += results["export_income"]
        aggregated[period]["pv_to_home_kwh"] += results["pv_to_home_kwh"]
        aggregated[period]["grid_to_battery_kwh"] += results["grid_to_battery_kwh"]
        aggregated[period]["intervals"] += 1
    
    return aggregated

def aggregate_by_month(all_results):
    """
    Aggregate half-hourly results by month.
    
    Args:
        all_results: List of tuples (month, results_dict)
    
    Returns:
        Dictionary with aggregated results per month
    """
    aggregated = {}
    
    for month, results in all_results:
        if month not in aggregated:
            aggregated[month] = {
                "import_kwh": 0,
                "import_cost": 0,
                "export_kwh": 0,
                "export_income": 0,
                "pv_to_home_kwh": 0,
                "grid_to_battery_kwh": 0
            }
        
        aggregated[month]["import_kwh"] += results["import_kwh"]
        aggregated[month]["import_cost"] += results["import_cost"]
        aggregated[month]["export_kwh"] += results["export_kwh"]
        aggregated[month]["export_income"] += results["export_income"]
        aggregated[month]["pv_to_home_kwh"] += results["pv_to_home_kwh"]
        aggregated[month]["grid_to_battery_kwh"] += results["grid_to_battery_kwh"]
    
    return aggregated