from config.settings import (
    IMPORT_PEAK_RATE, IMPORT_OFFPEAK_RATE,
    EXPORT_PEAK_RATE, EXPORT_OFFPEAK_RATE,
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

def get_rate(is_peak, rate_type):
    """
    Get the appropriate rate based on peak/off-peak and type (import/export).
    """
    if rate_type == "import":
        return IMPORT_PEAK_RATE if is_peak else IMPORT_OFFPEAK_RATE
    elif rate_type == "export":
        return EXPORT_PEAK_RATE if is_peak else EXPORT_OFFPEAK_RATE
    else:
        raise ValueError(f"Invalid rate_type: {rate_type}")

def calculate_return_for_interval(import_consumption, export_consumption, 
                                  interval_start, self_use_kwh=0):
    """
    Calculate return for a single half-hour interval with peak/off-peak rates.
    
    Args:
        import_consumption: kWh imported in this interval
        export_consumption: kWh exported in this interval
        interval_start: ISO format timestamp string
        self_use_kwh: kWh self-consumed in this interval
    
    Returns:
        Dictionary with calculated values for this interval
    """
    peak = is_peak_hour(interval_start)
    
    import_rate = get_rate(peak, "import")
    export_rate = get_rate(peak, "export")
    
    self_use_savings = self_use_kwh * import_rate
    export_income = export_consumption * export_rate
    import_cost = import_consumption * import_rate
    
    net = self_use_savings + export_income - import_cost
    
    return {
        "import (kwh)": import_consumption,
        "import cost": import_cost,
        "export (kwh)": export_consumption,
        "export income": export_income,
        "self use (kwh)": self_use_kwh,
        "self use savings": self_use_savings,
        "is_peak": peak,
        "net return": net
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
            "import (kwh)": 0,
            "import cost": 0,
            "export (kwh)": 0,
            "export income": 0,
            "self use (kwh)": 0,
            "self use savings": 0,
            "net return": 0,
            "intervals": 0
        },
        "off-peak": {
            "import (kwh)": 0,
            "import cost": 0,
            "export (kwh)": 0,
            "export income": 0,
            "self use (kwh)": 0,
            "self use savings": 0,
            "net return": 0,
            "intervals": 0
        }
    }
    
    for _, results in all_results:
        period = "peak" if results["is_peak"] else "off-peak"
        
        aggregated[period]["import (kwh)"] += results["import (kwh)"]
        aggregated[period]["import cost"] += results["import cost"]
        aggregated[period]["export (kwh)"] += results["export (kwh)"]
        aggregated[period]["export income"] += results["export income"]
        aggregated[period]["self use (kwh)"] += results["self use (kwh)"]
        aggregated[period]["self use savings"] += results["self use savings"]
        aggregated[period]["net return"] += results["net return"]
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
                "import (kwh)": 0,
                "import cost": 0,
                "export (kwh)": 0,
                "export income": 0,
                "self use (kwh)": 0,
                "self use savings": 0,
                "net return": 0
            }
        
        aggregated[month]["import (kwh)"] += results["import (kwh)"]
        aggregated[month]["import cost"] += results["import cost"]
        aggregated[month]["export (kwh)"] += results["export (kwh)"]
        aggregated[month]["export income"] += results["export income"]
        aggregated[month]["self use (kwh)"] += results["self use (kwh)"]
        aggregated[month]["self use savings"] += results["self use savings"]
        aggregated[month]["net return"] += results["net return"]
    
    return aggregated

def calculate_return(import_kwh, export_kwh, self_use_kwh):
    """Legacy function for backward compatibility."""
    # This would only work with fixed rates - kept for compatibility
    from config.settings import IMPORT_RATE, EXPORT_RATE
    
    self_use_savings = self_use_kwh * IMPORT_RATE
    export_income = export_kwh * EXPORT_RATE
    import_cost = import_kwh * IMPORT_RATE

    net = self_use_savings + export_income - import_cost

    return {
        "import (kwh)": import_kwh,
        "import cost": import_cost,
        "export (kwh)": export_kwh,
        "export income": export_income,
        "net return": net
    }