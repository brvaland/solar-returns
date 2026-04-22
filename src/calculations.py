from config.settings import (
    PEAK_START_HOUR, PEAK_END_HOUR, OFFPEAK_START_HOUR, OFFPEAK_END_HOUR, ACTIVE_TARIFF_NAME
)
from datetime import datetime
from zoneinfo import ZoneInfo

def get_rate_period(interval_start_str):
    """
    Determine the rate period for a given interval in UK timezone.
    Returns: 'peak', 'offpeak', or 'standard'
    
    For 2-rate tariffs: returns 'peak' or 'offpeak'
    For 3-rate tariffs: returns 'peak', 'offpeak', or 'standard'
    """
    # Parse the ISO timestamp
    dt = datetime.fromisoformat(interval_start_str.replace('Z', '+00:00'))
    
    # Convert to UK timezone (Europe/London)
    uk_tz = ZoneInfo("Europe/London")
    dt_uk = dt.astimezone(uk_tz)
    
    hour = dt_uk.hour
    
    # Check peak hours
    if PEAK_START_HOUR <= hour < PEAK_END_HOUR:
        return 'peak'
    
    # Check off-peak hours
    if ACTIVE_TARIFF_NAME == 'OCTOPUS_INTELLI_FLUX':
        return 'offpeak'
    else:
        # For 3-rate tariffs, determine off-peak hours with wrap-around logic
        if OFFPEAK_START_HOUR <= hour < OFFPEAK_END_HOUR:
            return 'offpeak'
        else:
            return 'standard'
    
def is_peak_hour(interval_start_str):
    """
    Determine if a given interval is during peak hours in UK timezone.
    (DEPRECATED: use get_rate_period() instead)
    """
    return get_rate_period(interval_start_str) == 'peak'

def get_rate(rate_period, rate_type, import_peak_rate, import_offpeak_rate, export_peak_rate, 
             export_offpeak_rate, import_standard_rate=None, export_standard_rate=None):
    """
    Get the appropriate rate based on rate period and type (import/export).
    Supports 2-rate (peak/offpeak) and 3-rate (peak/standard/offpeak) tariffs.
    
    Args:
        rate_period: 'peak', 'offpeak', or 'standard'
        rate_type: 'import' or 'export'
        import_peak_rate, import_offpeak_rate: Required rates
        export_peak_rate, export_offpeak_rate: Required rates
        import_standard_rate, export_standard_rate: Optional rates for 3-rate tariffs
    """
    if rate_type == "import":
        if rate_period == "peak":
            return import_peak_rate
        elif rate_period == "offpeak":
            return import_offpeak_rate
        elif rate_period == "standard":
            return import_standard_rate or import_offpeak_rate  # Fallback to offpeak if no standard
        else:
            raise ValueError(f"Invalid rate_period: {rate_period}")
    elif rate_type == "export":
        if rate_period == "peak":
            return export_peak_rate
        elif rate_period == "offpeak":
            return export_offpeak_rate
        elif rate_period == "standard":
            return export_standard_rate or export_offpeak_rate  # Fallback to offpeak if no standard
        else:
            raise ValueError(f"Invalid rate_period: {rate_period}")
    else:
        raise ValueError(f"Invalid rate_type: {rate_type}")

def calculate_return_for_interval(import_consumption, export_consumption, 
                                  interval_start, pv_to_home_kwh=0, grid_to_battery_kwh=0,
                                  import_peak_rate=None, import_offpeak_rate=None, import_standard_rate=None,
                                  export_peak_rate=None, export_offpeak_rate=None, export_standard_rate=None):
    """
    Calculate return for a single half-hour interval with peak/off-peak/standard rates.
    
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
        import_standard_rate: Standard import rate for 3-rate tariffs (optional)
        export_standard_rate: Standard export rate for 3-rate tariffs (optional)
    
    Returns:
        Dictionary with calculated values for this interval
    """
    # Import defaults from settings if not provided
    if import_peak_rate is None or import_offpeak_rate is None or export_peak_rate is None or export_offpeak_rate is None or import_standard_rate is None or export_standard_rate is None:
        from config.settings import IMPORT_PEAK_RATE, IMPORT_OFFPEAK_RATE, EXPORT_PEAK_RATE, EXPORT_OFFPEAK_RATE
        from config.settings import IMPORT_STANDARD_RATE, EXPORT_STANDARD_RATE
        import_peak_rate = import_peak_rate or IMPORT_PEAK_RATE
        import_offpeak_rate = import_offpeak_rate or IMPORT_OFFPEAK_RATE
        export_peak_rate = export_peak_rate or EXPORT_PEAK_RATE
        export_offpeak_rate = export_offpeak_rate or EXPORT_OFFPEAK_RATE
        import_standard_rate = import_standard_rate or IMPORT_STANDARD_RATE
        export_standard_rate = export_standard_rate or EXPORT_STANDARD_RATE
    
    period = get_rate_period(interval_start)
    
    import_rate = get_rate(period, "import", import_peak_rate, import_offpeak_rate, 
                          export_peak_rate, export_offpeak_rate, import_standard_rate, export_standard_rate)
    export_rate = get_rate(period, "export", import_peak_rate, import_offpeak_rate, 
                          export_peak_rate, export_offpeak_rate, import_standard_rate, export_standard_rate)
    
    export_income = export_consumption * export_rate
    import_cost = import_consumption * import_rate
    
    return {
        "import_kwh": import_consumption,
        "import_cost": import_cost,
        "export_kwh": export_consumption,
        "export_income": export_income,
        "pv_to_home_kwh": pv_to_home_kwh,
        "grid_to_battery_kwh": grid_to_battery_kwh,
        "is_peak": period == 'peak',
        "rate_period": period
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