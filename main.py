import logging
from src.octopus_api import get_import_consumption, get_export_consumption
from src.calculations import calculate_return_for_interval, aggregate_by_peak_offpeak
from src.excel_writer import update_excel
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting solar return calculation")

    # Define the day you want
    target_date_from = "2026-03-04T00:00:00Z"
    target_date_to = "2026-04-01T00:00:00Z"
    logger.info(f"Date range: {target_date_from} to {target_date_to}")

    logger.info("Fetching import consumption data...")
    import_data = get_import_consumption(target_date_from, target_date_to)
    logger.info(f"Retrieved {len(import_data)} import data points")
    
    logger.info("Fetching export consumption data...")
    export_data = get_export_consumption(target_date_from, target_date_to)
    logger.info(f"Retrieved {len(export_data)} export data points")

    # Create a map of export data by interval_start for easy lookup
    export_by_interval = {d["interval_start"]: float(d["consumption"]) for d in export_data}

    # Process each half-hourly import record
    all_results = []
    logger.info(f"Processing {len(import_data)} half-hourly intervals...")
    
    for import_record in import_data:
        interval_start = import_record["interval_start"]
        import_kwh = float(import_record["consumption"])
        
        # Get corresponding export data for this interval
        export_kwh = export_by_interval.get(interval_start, 0)
        
        # TEMP assumption: no self-use (replace later with actual self-use calculation)
        self_use_kwh = 0
        
        # Calculate return for this half-hour interval
        results = calculate_return_for_interval(
            import_kwh, export_kwh, interval_start, self_use_kwh
        )
        
        # Extract month from interval_start
        month = interval_start[:7]  # YYYY-MM format
        
        all_results.append((month, results))
        logger.debug(f"Interval {interval_start}: import={import_kwh}, export={export_kwh}, "
                    f"is_peak={results['is_peak']}, net_return={results['net return']:.4f}")

    # Aggregate results by peak and off-peak
    peak_offpeak_results = aggregate_by_peak_offpeak(all_results)
    
    # Sum peak and off-peak into a single row
    total_results = {
        "import (kwh)": 0,
        "import cost": 0,
        "export (kwh)": 0,
        "export income": 0,
        "self use (kwh)": 0,
        "self use savings": 0,
        "net return": 0,
        "intervals": 0
    }
    
    for period in ["peak", "off-peak"]:
        for key in total_results.keys():
            total_results[key] += peak_offpeak_results[period][key]
    
    # Extract intervals count for logging before removing from results
    intervals_count = total_results["intervals"]
    
    # Remove intervals column from results (not needed in Excel)
    total_results.pop("intervals", None)
    
    # Extract primary month from the data
    months_in_data = set(month for month, _ in all_results)
    primary_month = sorted(months_in_data)[0] if months_in_data else "Unknown"
    
    # Format date range as "DD-MMM:DD-MMM"
    date_from = datetime.fromisoformat(target_date_from.replace('Z', '+00:00'))
    date_to = datetime.fromisoformat(target_date_to.replace('Z', '+00:00'))
    # Subtract 1 day from target_date_to since it's the next day at 00:00
    date_to = date_to - timedelta(days=1)
    
    date_range = f"{date_from.strftime('%d-%b')}:{date_to.strftime('%d-%b')}"
    
    # Update Excel with aggregated results
    logger.info(f"Updating Excel with aggregated data for {date_range}")
    update_excel(total_results, month=date_range)
    logger.info(f"Added row for {date_range}: {intervals_count} intervals, "
                f"net return = {total_results['net return']:.2f}")

    logger.info(f"✅ Solar return updated successfully")

if __name__ == "__main__":
    main()