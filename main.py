import logging
import argparse
import os
import pandas as pd
from src.octopus_api import get_import_consumption, get_export_consumption
from src.givenergy_api import get_solar_generation
from src.calculations import calculate_return_for_interval, aggregate_by_peak_offpeak
from src.excel_writer import update_excel
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_default_dates_from_last_row(file_path="data/solar_return.xlsx"):
    """
    Read the last row from the Excel file and calculate next month's date range.
    If file doesn't exist or is empty, returns None.
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        # Read the Excel file
        xls = pd.ExcelFile(file_path)
        
        # Get the first sheet
        df = pd.read_excel(file_path, sheet_name=0)
        
        if df.empty:
            return None
        
        # Get the last row
        last_row = df.iloc[-1]
        month_value = last_row.get("date_range") or last_row.get("month")
        
        if not month_value:
            return None
        
        # Parse the month value (format: "04-Mar:31-Mar")
        if ":" in str(month_value):
            date_parts = str(month_value).split(":")
            end_date_str = date_parts[1].strip()  # "31-Mar"
        else:
            return None
        
        # Parse the end date to get the current month
        # Format is "DD-MMM" like "31-Mar"
        try:
            # Add current year to parse correctly
            current_year = datetime.now().year
            end_date = datetime.strptime(f"{end_date_str}-{current_year}", "%d-%b-%Y")
        except ValueError:
            return None
        
        # Calculate next month's dates (4th to last day of next month)
        next_month = end_date + relativedelta(days=1)  # Move to next day
        next_month_start = next_month.replace(day=4)  # Start of next month (4th)
        next_month_end = (next_month_start + relativedelta(months=1)) - timedelta(days=1)  # Last day of month
        
        # Format as ISO 8601
        target_date_from = next_month_start.strftime("%Y-%m-%dT00:00:00Z")
        target_date_to = (next_month_end + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        
        return (target_date_from, target_date_to)
    
    except Exception as e:
        logger.debug(f"Could not read default dates from Excel file: {e}")
        return None

def date_to_iso(date_str, is_end_date=False):
    """
    Convert simple date format (YYYY-MM-DD) to ISO format (YYYY-MM-DDTHH:MM:SSZ).
    If input is already in ISO format, return as-is.
    
    For end dates, automatically adds 1 day (represents end of day at 23:59:59).
    """
    if "T" in date_str:
        # Already in ISO format
        return date_str
    
    try:
        # Parse simple date format
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Add 1 day for end dates (to capture full day including last hour)
        if is_end_date:
            parsed = parsed + timedelta(days=1)
        
        return parsed.strftime("%Y-%m-%dT00:00:00Z")
    except ValueError:
        raise ValueError(f"Invalid date format. Please use YYYY-MM-DD (e.g., 2026-01-01)")

def extract_date_part(iso_date):
    """Extract YYYY-MM-DD part from ISO format date string."""
    if "T" in iso_date:
        return iso_date.split("T")[0]
    return iso_date

def prompt_for_tariff_selection():
    """
    Prompt user to select a tariff from available options.
    Returns tariff name and tariff definition.
    """
    from config.settings import TARIFF_DEFINITIONS
    
    print("\n" + "="*60)
    print("TARIFF SELECTION")
    print("="*60 + "\n")
    
    tariff_list = list(TARIFF_DEFINITIONS.items())
    for idx, (tariff_name, tariff_def) in enumerate(tariff_list, 1):
        print(f"{idx}. {tariff_name}")
        print(f"   {tariff_def['description']}")
        print(f"   Rate periods: {', '.join(tariff_def['rate_periods'])}")
        print()
    
    while True:
        try:
            choice = input(f"Select tariff (1-{len(tariff_list)}): ").strip()
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(tariff_list):
                tariff_name, tariff_def = tariff_list[choice_idx]
                print(f"\n✓ Selected: {tariff_name}\n")
                return tariff_name, tariff_def
            else:
                print(f"Error: Please enter a number between 1 and {len(tariff_list)}")
        except ValueError:
            print("Error: Please enter a valid number")

def prompt_for_rates(selected_tariff_name, tariff_def):
    """
    Prompt user for rates based on selected tariff type.
    Returns dict with import and export rates for each period.
    """
    rate_periods = tariff_def['rate_periods']
    print("="*60)
    print("RATE CONFIGURATION (press Enter to use defaults)")
    print("="*60 + "\n")
    
    from config.settings import (
        IMPORT_PEAK_RATE, IMPORT_OFFPEAK_RATE, IMPORT_STANDARD_RATE,
        EXPORT_PEAK_RATE, EXPORT_OFFPEAK_RATE, EXPORT_STANDARD_RATE
    )
    
    rates = {
        'peak': {'import': None, 'export': None},
        'standard': {'import': None, 'export': None},
        'offpeak': {'import': None, 'export': None}
    }
    
    # Map rate defaults
    rate_defaults = {
        'peak': {'import': IMPORT_PEAK_RATE, 'export': EXPORT_PEAK_RATE},
        'standard': {'import': IMPORT_STANDARD_RATE, 'export': EXPORT_STANDARD_RATE},
        'offpeak': {'import': IMPORT_OFFPEAK_RATE, 'export': EXPORT_OFFPEAK_RATE}
    }
    
    # Prompt for each rate period in the tariff
    for period in rate_periods:
        print(f"\n{period.upper()} RATE:")
        
        # Import rate
        import_default = rate_defaults[period]['import']
        import_input = input(f"  Import {period} rate (default: {import_default}): ").strip()
        if import_input:
            try:
                rates[period]['import'] = float(import_input)
            except ValueError:
                print(f"    Error: Invalid rate, using default {import_default}")
                rates[period]['import'] = import_default
        else:
            rates[period]['import'] = import_default
        
        # Export rate
        export_default = rate_defaults[period]['export']
        export_input = input(f"  Export {period} rate (default: {export_default}): ").strip()
        if export_input:
            try:
                rates[period]['export'] = float(export_input)
            except ValueError:
                print(f"    Error: Invalid rate, using default {export_default}")
                rates[period]['export'] = export_default
        else:
            rates[period]['export'] = export_default
    
    print()
    return rates

def main(target_date_from="2026-03-04T00:00:00Z", target_date_to="2026-04-01T00:00:00Z",
         import_peak_rate=None, import_offpeak_rate=None, export_peak_rate=None, export_offpeak_rate=None, baseline_rate=None):
    logger.info("Starting solar return calculation")
    logger.info(f"Date range: {target_date_from} to {target_date_to}")

    logger.info("Fetching import consumption data...")
    import_data = get_import_consumption(target_date_from, target_date_to)
    logger.info(f"Retrieved {len(import_data)} import data points")
    
    logger.info("Fetching export consumption data...")
    export_data = get_export_consumption(target_date_from, target_date_to)
    logger.info(f"Retrieved {len(export_data)} export data points")
    
    logger.info("Fetching GivEnergy solar generation data...")
    # Extract date parts for GivEnergy API (format: YYYY-MM-DD)
    solar_date_from = extract_date_part(target_date_from)
    solar_date_to = extract_date_part(target_date_to)
    solar_data = get_solar_generation(solar_date_from, solar_date_to)
    logger.info(f"Retrieved {len(solar_data)} solar data points")

    # Create a map of export data by interval_start for easy lookup
    export_by_interval = {d["interval_start"]: float(d["consumption"]) for d in export_data}
    
    # Create a map of solar interval data by interval_start for easy lookup
    # Convert GivEnergy start_time format ("2025-09-01 00:00") to octopus format ("2025-09-01T00:00:00Z")
    solar_by_interval = {}
    for item in solar_data:
        try:
            # Parse GivEnergy format and convert to ISO format with Z suffix
            givenergy_time = datetime.strptime(item["start_time"], "%Y-%m-%d %H:%M")
            octopus_time = givenergy_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            pv_to_home_kwh = float(item["data"].get("0", 0))
            grid_to_battery_kwh = float(item["data"].get("4", 0))
            solar_by_interval[octopus_time] = {
                "pv_to_home_kwh": pv_to_home_kwh,
                "grid_to_battery_kwh": grid_to_battery_kwh
            }
        except (ValueError, KeyError) as e:
            logger.debug(f"Could not parse solar data item: {e}")
    
    logger.info(f"Solar data mapped to {len(solar_by_interval)} intervals")
    if solar_by_interval:
        sample_keys = list(solar_by_interval.keys())[:3]
        logger.info(f"Sample solar interval times: {sample_keys}")
    else:
        logger.warning("No solar intervals were mapped from GivEnergy data")

    # Process each half-hourly import record
    all_results = []
    logger.info(f"Processing {len(import_data)} half-hourly intervals...")
    
    if import_data:
        sample_interval = import_data[0]["interval_start"]
        logger.info(f"Sample import interval_start format: {sample_interval}")
    
    non_zero_solar_count = 0
    for import_record in import_data:
        interval_start = import_record["interval_start"]
        import_kwh = float(import_record["consumption"])
        
        # Get corresponding export data for this interval
        export_kwh = export_by_interval.get(interval_start, 0)
        
        # Convert interval_start to UTC/Z format to match solar data
        # Handle both "2026-04-01T01:00:00+01:00" and "2026-04-01T00:00:00Z" formats
        try:
            dt = datetime.fromisoformat(interval_start)
            utc_interval = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, AttributeError):
            # Fallback if datetime.timezone not available or parse fails
            utc_interval = interval_start
        
        # Get PV to home and grid-to-battery data from GivEnergy API
        interval_solar_data = solar_by_interval.get(
            utc_interval,
            {"pv_to_home_kwh": 0, "grid_to_battery_kwh": 0}
        )
        pv_to_home_kwh = interval_solar_data["pv_to_home_kwh"]
        grid_to_battery_kwh = interval_solar_data["grid_to_battery_kwh"]
        
        if pv_to_home_kwh > 0 or grid_to_battery_kwh > 0:
            non_zero_solar_count += 1
        
        # Calculate return for this half-hour interval
        results = calculate_return_for_interval(
            import_kwh, export_kwh, interval_start,
            pv_to_home_kwh, grid_to_battery_kwh,
            import_peak_rate, import_offpeak_rate, export_peak_rate, export_offpeak_rate
        )
        
        # Extract month from interval_start
        month = interval_start[:7]  # YYYY-MM format
        
        all_results.append((month, results))
        logger.debug(f"Interval {interval_start}: import={import_kwh}, export={export_kwh}, "
                    f"pv_to_home_kwh={pv_to_home_kwh}, grid_to_battery_kwh={grid_to_battery_kwh}, "
                    f"is_peak={results['is_peak']}")

    logger.info(f"Found {non_zero_solar_count} intervals with PV or grid-to-battery data out of {len(import_data)} intervals")

    # Aggregate results by peak and off-peak
    peak_offpeak_results = aggregate_by_peak_offpeak(all_results)
    
    # Sum peak and off-peak into a single row
    total_results = {
        "import_kwh": 0,
        "import_cost": 0,
        "export_kwh": 0,
        "export_income": 0,
        "pv_to_home_kwh": 0,
        "grid_to_battery_kwh": 0,
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
    year = date_from.strftime('%Y')
    
    # Update Excel with aggregated results
    logger.info(f"Updating Excel with aggregated data for {date_range}")
    update_excel(total_results, date_range=date_range, sheet_name=year, baseline_rate=baseline_rate)
    logger.info(f"Added row for {date_range}: {intervals_count} intervals")

    logger.info(f"✅ Solar return updated successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="☀️  Solar Return Calculator - Calculate your solar import/export returns",
        add_help=False
    )
    parser.add_argument(
        "--from",
        dest="target_date_from",
        default=None,
        help="Start date in YYYY-MM-DD format (e.g., 2026-01-01)"
    )
    parser.add_argument(
        "--to",
        dest="target_date_to",
        default=None,
        help="End date in YYYY-MM-DD format (e.g., 2026-02-04)"
    )
    parser.add_argument(
        "--import-peak-rate",
        dest="import_peak_rate",
        type=float,
        default=None,
        help="Import peak rate (default: 0.2855)"
    )
    parser.add_argument(
        "--import-offpeak-rate",
        dest="import_offpeak_rate",
        type=float,
        default=None,
        help="Import off-peak rate (default: 0.2141)"
    )
    parser.add_argument(
        "--export-peak-rate",
        dest="export_peak_rate",
        type=float,
        default=None,
        help="Export peak rate (default: 0.3142)"
    )
    parser.add_argument(
        "--export-offpeak-rate",
        dest="export_offpeak_rate",
        type=float,
        default=None,
        help="Export off-peak rate (default: 0.2357)"
    )
    parser.add_argument(
        "--baseline-rate",
        dest="baseline_rate",
        type=float,
        default=None,
        help="Baseline rate (default: 0.2498)"
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show help message"
    )
    
    args = parser.parse_args()
    
    # Show help if requested
    if args.help:
        print("\n" + "="*60)
        print("☀️  SOLAR RETURN CALCULATOR")
        print("="*60)
        print("\nThis utility calculates your solar panel returns by:")
        print("  • Fetching half-hourly import/export consumption data")
        print("  • Applying peak (16:00-19:00) and off-peak rates")
        print("  • Calculating import costs and export income")
        print("  • Exporting results to Excel with professional formatting")
        print("\nUsage:")
        print("  poetry run python main.py")
        print("    → Interactive mode (prompts for dates and rates)")
        print("\n  poetry run python main.py --from 2026-01-01 --to 2026-02-03")
        print("    → Command-line mode with specific dates")
        print("    (Note: end date automatically adds 1 day, so 02-03 becomes 02-04)")
        print("\n  poetry run python main.py --from 2026-01-01 --to 2026-02-03 \\")
        print("    --import-offpeak-rate 0.2141 --import-peak-rate 0.2855 \\")
        print("    --export-offpeak-rate 0.2357 --export-peak-rate 0.3142 \\")
        print("    --baseline-rate 0.2498")
        print("    → Command-line mode with custom rates")
        print("\nDate format: YYYY-MM-DD (e.g., 2026-01-01)")
        print("Rate format: Decimal (e.g., 0.2855 for £0.2855/kWh)")
        print("="*60 + "\n")
        exit(0)
    
    # Convert command-line dates to ISO format if provided
    if args.target_date_from:
        try:
            args.target_date_from = date_to_iso(args.target_date_from, is_end_date=False)
        except ValueError as e:
            print(f"Error parsing start date: {e}")
            exit(1)
    
    if args.target_date_to:
        try:
            args.target_date_to = date_to_iso(args.target_date_to, is_end_date=True)
        except ValueError as e:
            print(f"Error parsing end date: {e}")
            exit(1)
    
    # Interactive mode if no dates provided
    if args.target_date_from is None or args.target_date_to is None:
        print("\n" + "="*60)
        print("☀️  SOLAR RETURN CALCULATOR")
        print("="*60)
        print("\nThis utility calculates your solar import/export returns")
        print("with peak (16:00-19:00) and off-peak rate calculations.\n")
        print("Results are saved to Excel with professional formatting.")
        print("You will be prompted for tariff selection, rates and dates.\n")
        
        # Step 1: Tariff selection
        selected_tariff_name, selected_tariff_def = prompt_for_tariff_selection()
        
        # Step 2: Rate input based on tariff
        rates_dict = prompt_for_rates(selected_tariff_name, selected_tariff_def)
        
        # Map rates to the function parameters
        args.import_peak_rate = rates_dict['peak']['import']
        args.export_peak_rate = rates_dict['peak']['export']
        args.import_offpeak_rate = rates_dict['offpeak']['import']
        args.export_offpeak_rate = rates_dict['offpeak']['export']
        
        # Import baseline rate from settings
        from config.settings import BASELINE_RATE
        baseline_input = input(f"Enter baseline rate (default: {BASELINE_RATE}): ").strip()
        if baseline_input:
            try:
                args.baseline_rate = float(baseline_input)
            except ValueError:
                print(f"Error: Invalid baseline rate '{baseline_input}', using default {BASELINE_RATE}")
                args.baseline_rate = BASELINE_RATE
        else:
            args.baseline_rate = BASELINE_RATE
        
        # Save the selected tariff and rates to config.yaml for future use (flat structure)
        try:
            import yaml
            config_file_path = "config.yaml"
            
            # Read existing config if it exists
            config_data = {}
            if os.path.exists(config_file_path):
                with open(config_file_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            
            # Add tariff name at top level
            config_data['TARIFF'] = selected_tariff_name
            
            # Update rates section (flat structure)
            if 'rates' not in config_data:
                config_data['rates'] = {}
            
            # Add all rate periods (import and export)
            for period in selected_tariff_def['rate_periods']:
                config_data['rates'][f'import_{period}_rate'] = rates_dict[period]['import']
                config_data['rates'][f'export_{period}_rate'] = rates_dict[period]['export']
            
            # Preserve baseline rate at top level
            if args.baseline_rate is not None:
                config_data['baseline_rate'] = args.baseline_rate
            
            # Write back to config.yaml
            with open(config_file_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"✓ Tariff '{selected_tariff_name}' and rates saved to {config_file_path}")
            
        except ImportError:
            print("Warning: PyYAML not available, tariff not saved")
        except Exception as e:
            print(f"Warning: Could not save tariff to config.yaml: {e}")
        
        print("\n" + "="*60)
        print("DATE CONFIGURATION")
        print("="*60)
        
        # Try to get defaults from last row in Excel file
        auto_dates = get_default_dates_from_last_row()
        if auto_dates:
            default_from, default_to = auto_dates
            # Extract 3rd of the month for display (code already has 4th)
            default_to_dt = datetime.fromisoformat(default_to.replace('Z', '+00:00'))
            default_to_display = (default_to_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            print("\n✓ Auto-detected next bill cycle from Excel history")
        else:
            # Default to January 1 to February 3 (code adds 1 day automatically)
            current_year = datetime.now().year
            jan_start = datetime(current_year, 1, 1)
            feb_3rd = datetime(current_year, 2, 3)
            
            default_from = jan_start.strftime("%Y-%m-%dT00:00:00Z")
            default_to_display = feb_3rd.strftime("%Y-%m-%d")
            default_to = (feb_3rd + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
            print(f"\n(No existing data found - defaulting to Jan 1 - Feb 3, {current_year})")
        
        # Extract date parts for display (YYYY-MM-DD format)
        default_from_display = extract_date_part(default_from)
        
        date_from_input = input(f"\nEnter start date YYYY-MM-DD (default: {default_from_display}): ").strip()
        if date_from_input:
            try:
                args.target_date_from = date_to_iso(date_from_input, is_end_date=False)
            except ValueError as e:
                print(f"Error: {e}")
                args.target_date_from = default_from
        else:
            args.target_date_from = default_from
        
        date_to_input = input(f"Enter end date YYYY-MM-DD (default: {default_to_display}): ").strip()
        if date_to_input:
            try:
                args.target_date_to = date_to_iso(date_to_input, is_end_date=True)
            except ValueError as e:
                print(f"Error: {e}")
                args.target_date_to = default_to
        else:
            args.target_date_to = default_to
        
        print("="*60 + "\n")
    
    main(args.target_date_from, args.target_date_to, 
         args.import_peak_rate, args.import_offpeak_rate, args.export_peak_rate, args.export_offpeak_rate, args.baseline_rate)