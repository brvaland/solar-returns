from dotenv import load_dotenv
import os

load_dotenv()

# ============================================================================
# TARIFF DEFINITIONS - Hardcoded hours per tariff
# ============================================================================

TARIFF_DEFINITIONS = {
    'OCTOPUS_INTELLI_FLUX': {
        'description': 'Integration Flux - 2 rates (peak and off-peak)',
        'rate_periods': ['offpeak', 'peak'],
        'hours': {
            'peak_start': 16,
            'peak_end': 19,
            'offpeak_start': 19,
            'offpeak_end': 16
        }
    },
    'OCTOPUS_FLUX': {
        'description': 'Standard Flux - 3 rates (peak, standard, and off-peak)',
        'rate_periods': ['offpeak', 'standard', 'peak'],
        'hours': {
            'peak_start': 16,
            'peak_end': 19,
            'offpeak_start': 1,
            'offpeak_end': 5
        }
    }
}

# Load user preferences from config.yaml
user_config = {}
try:
    import yaml
    config_file = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            user_config = yaml.safe_load(f) or {}
except ImportError:
    pass  # YAML not available, use defaults
except Exception:
    pass  # Config file error, use defaults


def get_active_tariff():
    """
    Get the currently active tariff configuration.
    Reads TARIFF attribute from top level of config.yaml.
    """
    tariff_name = user_config.get('TARIFF')
    
    # If tariff name is specified and exists in definitions, use it
    if tariff_name and tariff_name in TARIFF_DEFINITIONS:
        tariff_def = TARIFF_DEFINITIONS[tariff_name]
        return tariff_name, tariff_def
    
    # Fallback to first tariff definition if not specified
    if TARIFF_DEFINITIONS:
        first_tariff_name = list(TARIFF_DEFINITIONS.keys())[0]
        first_tariff_def = TARIFF_DEFINITIONS[first_tariff_name]
        return first_tariff_name, first_tariff_def
    
    return None, {}

# API Configuration (from .env)
OCTOPUS_API_URI = os.getenv("OCTOPUS_API_URI")
OCTOPUS_API_KEY = os.getenv("OCTOPUS_API_KEY")

EXPORT_MPAN = os.getenv("EXPORT_MPAN")
IMPORT_MPAN = os.getenv("IMPORT_MPAN")
METER_SERIAL = os.getenv("METER_SERIAL")

GIVENERGY_API_URI = os.getenv("GIVENERGY_API_URI")
GIVENERGY_DEVICE_ID = os.getenv("GIVENERGY_DEVICE_ID")
GIVENERGY_API_KEY = os.getenv("GIVENERGY_API_KEY")

# Get active tariff
ACTIVE_TARIFF_NAME, active_tariff_config = get_active_tariff()

# Extract rates directly from config.yaml rates section (flat structure)
rates_config = user_config.get('rates', {})

# Peak and Off-peak rates (from config.yaml rates section)
IMPORT_PEAK_RATE = rates_config.get('import_peak_rate', 0)
IMPORT_OFFPEAK_RATE = rates_config.get('import_offpeak_rate', 0)
IMPORT_STANDARD_RATE = rates_config.get('import_standard_rate', 0)  # For 3-rate tariffs
EXPORT_PEAK_RATE = rates_config.get('export_peak_rate', 0)
EXPORT_OFFPEAK_RATE = rates_config.get('export_offpeak_rate', 0)
EXPORT_STANDARD_RATE = rates_config.get('export_standard_rate', 0)  # For 3-rate tariffs

BASELINE_RATE = user_config.get('baseline_rate', 0)

# Peak hours from active tariff definition (from hardcoded TARIFF_DEFINITIONS)
if ACTIVE_TARIFF_NAME and ACTIVE_TARIFF_NAME in TARIFF_DEFINITIONS:
    tariff_def_hours = TARIFF_DEFINITIONS[ACTIVE_TARIFF_NAME]['hours']
    PEAK_START_HOUR = tariff_def_hours.get('peak_start', 16)
    PEAK_END_HOUR = tariff_def_hours.get('peak_end', 19)
    OFFPEAK_START_HOUR = tariff_def_hours.get('offpeak_start', 19)
    OFFPEAK_END_HOUR = tariff_def_hours.get('offpeak_end', 16)
else:
    # Defaults
    PEAK_START_HOUR = 16  # 16:00
    PEAK_END_HOUR = 19    # 19:00
    OFFPEAK_START_HOUR = 19
    OFFPEAK_END_HOUR = 16