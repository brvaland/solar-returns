import logging
from src.octopus_api import get_import_consumption, get_export_consumption
from src.calculations import calculate_return_for_interval, aggregate_by_peak_offpeak
from src.excel_writer import update_excel
from datetime import datetime

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
    
    # Update Excel with peak/off-peak aggregated results
    logger.info(f"Updating Excel with peak and off-peak data")
    for period in ["peak", "off-peak"]:
        results = peak_offpeak_results[period]
        update_excel(results, month=period)
        logger.info(f"Added row for {period}: {results['intervals']} intervals, "
                    f"net return = {results['net return']:.2f}")

    logger.info(f"✅ Solar return updated successfully")

if __name__ == "__main__":
    main()