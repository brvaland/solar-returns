from dotenv import load_dotenv
import os

load_dotenv()

OCTOPUS_API_URI = os.getenv("OCTOPUS_API_URI")
OCTOPUS_API_KEY = os.getenv("OCTOPUS_API_KEY")

EXPORT_MPAN = os.getenv("EXPORT_MPAN")
IMPORT_MPAN = os.getenv("IMPORT_MPAN")
METER_SERIAL = os.getenv("METER_SERIAL")

GIVENERGY_API_URI = os.getenv("GIVENERGY_API_URI")
GIVENERGY_DEVICE_ID = os.getenv("GIVENERGY_DEVICE_ID")
GIVENERGY_API_KEY = os.getenv("GIVENERGY_API_KEY")

# Peak and Off-peak rates
IMPORT_PEAK_RATE = 0.2820  # 16:00 - 19:00
IMPORT_OFFPEAK_RATE = 0.2125  # 19:00 - 16:00
EXPORT_PEAK_RATE = 0.2820  # 16:00 - 19:00
EXPORT_OFFPEAK_RATE = 0.2125  # 19:00 - 16:00

# Peak hours (24-hour format)
PEAK_START_HOUR = 16  # 16:00
PEAK_END_HOUR = 19  # 19:00

# Legacy rates (for backward compatibility)
IMPORT_RATE = float(os.getenv("IMPORT_RATE", "0.24"))
EXPORT_RATE = float(os.getenv("EXPORT_RATE", "0.24"))