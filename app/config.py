import os

# Base URL of the upstream Hospital Directory API
HOSPITAL_API_BASE = os.getenv(
    "HOSPITAL_API_BASE", "https://hospital-directory.onrender.com"
)

# The spec caps bulk uploads at 20 rows
MAX_CSV_ROWS = int(os.getenv("MAX_CSV_ROWS", 20))

# How long (seconds) to wait for each API call before giving up
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 15))
