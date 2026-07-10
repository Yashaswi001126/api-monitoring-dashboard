"""
config.py
---------
Central place for all application settings.

Why this file exists:
Instead of scattering "magic values" (file paths, intervals, URLs) across
multiple files, we keep them here. If you need to change how often APIs
are checked, or where the database lives, you only change it in ONE place.
"""

import json
import os

# ---------------------------------------------------------------------------
# Base directory of the project (used to build absolute paths safely,
# so the app works no matter where you run it from).
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Database settings
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)  # make sure the folder exists

DATABASE_PATH = os.path.join(DATA_DIR, "monitoring.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ---------------------------------------------------------------------------
# Logging settings
# ---------------------------------------------------------------------------
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOGS_DIR, "monitoring.log")

# ---------------------------------------------------------------------------
# Monitoring settings
# ---------------------------------------------------------------------------
CHECK_INTERVAL_SECONDS = 60      # how often APScheduler runs the checks
REQUEST_TIMEOUT_SECONDS = 5      # how long to wait before treating a call as a timeout

# ---------------------------------------------------------------------------
# FastAPI backend settings
# ---------------------------------------------------------------------------
API_HOST = "127.0.0.1"
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ---------------------------------------------------------------------------
# Load the list of APIs to monitor from sample_apis.json
# ---------------------------------------------------------------------------
APIS_CONFIG_PATH = os.path.join(BASE_DIR, "sample_apis.json")


def load_monitored_apis() -> list[dict]:
    """
    Reads sample_apis.json and returns a list of API entries to monitor.

    Each entry looks like:
        {"name": "GitHub API", "url": "https://api.github.com"}

    Returns an empty list (with a printed warning) if the file is missing
    or malformed, so the app doesn't crash on startup.
    """
    try:
        with open(APIS_CONFIG_PATH, "r") as f:
            data = json.load(f)
            return data.get("apis", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[config] Warning: could not load {APIS_CONFIG_PATH}: {e}")
        return []


MONITORED_APIS = load_monitored_apis()
