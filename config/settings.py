from dotenv import load_dotenv
import os

load_dotenv()

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

# API Configuration (from .env)
OCTOPUS_API_URI = os.getenv("OCTOPUS_API_URI")
OCTOPUS_API_KEY = os.getenv("OCTOPUS_API_KEY")

EXPORT_MPAN = os.getenv("EXPORT_MPAN")
IMPORT_MPAN = os.getenv("IMPORT_MPAN")
METER_SERIAL = os.getenv("METER_SERIAL")

GIVENERGY_API_URI = os.getenv("GIVENERGY_API_URI")
GIVENERGY_DEVICE_ID = os.getenv("GIVENERGY_DEVICE_ID")
GIVENERGY_API_KEY = os.getenv("GIVENERGY_API_KEY")

# Peak and Off-peak rates (from config.yaml with .env fallbacks)
IMPORT_PEAK_RATE = user_config.get('rates', {}).get('import_peak_rate', 0)  # 16:00 - 19:00
IMPORT_OFFPEAK_RATE = user_config.get('rates', {}).get('import_offpeak_rate', 0)  # 19:00 - 16:00
EXPORT_PEAK_RATE = user_config.get('rates', {}).get('export_peak_rate', 0)  # 16:00 - 19:00
EXPORT_OFFPEAK_RATE = user_config.get('rates', {}).get('export_offpeak_rate', 0)  # 19:00 - 16:00

BASELINE_RATE = user_config.get('rates', {}).get('baseline_rate', 0)

# Peak hours (24-hour format)
PEAK_START_HOUR = 16  # 16:00
PEAK_END_HOUR = 19  # 19:00