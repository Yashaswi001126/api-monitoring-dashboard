"""
monitor.py
----------
The heart of the app: checks a single API's health, or loops through
every configured API and records the results. This is the function the
scheduler calls every 60 seconds.

Error handling philosophy:
Every possible failure (invalid URL, timeout, connection refused, DNS
failure, unexpected exception) is caught explicitly and turned into a
clean database row with is_success=False and a readable error_message
— the app should NEVER crash because a monitored API is down or broken.
That resilience is the whole point of a monitoring tool.
"""

import time
import requests
from sqlalchemy.orm import Session

from backend.config import REQUEST_TIMEOUT_SECONDS, MONITORED_APIS
from backend.database import SessionLocal
from backend.utils import is_valid_url
from backend.logger import get_logger
from backend import crud

logger = get_logger(__name__)


def check_api(db: Session, api_name: str, url: str) -> dict:
    """
    Performs a single health check against one API and saves the result
    to the database.

    Returns the result as a dict (useful for logging/testing), but the
    persisted database row is the "source of truth" for the dashboard.
    """

    # --- Guard 1: reject obviously invalid URLs before making a request ---
    if not is_valid_url(url):
        error_message = f"Invalid URL format: '{url}'"
        logger.warning(f"[{api_name}] {error_message}")
        log = crud.create_log(
            db,
            api_name=api_name,
            url=url,
            status_code=None,
            response_time_ms=None,
            is_success=False,
            error_message=error_message,
        )
        return log.to_dict()

    start_time = time.perf_counter()

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Treat any 2xx or 3xx status as "success". 4xx/5xx are recorded
        # but marked as failures since the API isn't healthy.
        success = response.status_code < 400

        if success:
            logger.info(
                f"[{api_name}] OK - status={response.status_code} "
                f"time={elapsed_ms}ms"
            )
        else:
            logger.warning(
                f"[{api_name}] Non-success status={response.status_code} "
                f"time={elapsed_ms}ms"
            )

        log = crud.create_log(
            db,
            api_name=api_name,
            url=url,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            is_success=success,
            error_message=None if success else f"HTTP {response.status_code}",
        )
        return log.to_dict()

    except requests.exceptions.Timeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_message = f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s"
        logger.error(f"[{api_name}] {error_message}")
        log = crud.create_log(
            db, api_name, url, None, elapsed_ms, False, error_message
        )
        return log.to_dict()

    except requests.exceptions.ConnectionError:
        error_message = "Connection error (DNS failure, refused, or unreachable)"
        logger.error(f"[{api_name}] {error_message}")
        log = crud.create_log(
            db, api_name, url, None, None, False, error_message
        )
        return log.to_dict()

    except requests.exceptions.RequestException as e:
        # Catch-all for any other 'requests' library error
        # (e.g. too many redirects, malformed headers).
        error_message = f"Request failed: {str(e)}"
        logger.error(f"[{api_name}] {error_message}")
        log = crud.create_log(
            db, api_name, url, None, None, False, error_message
        )
        return log.to_dict()

    except Exception as e:
        # Last-resort safety net so one broken API never crashes the
        # entire scheduled job.
        error_message = f"Unexpected error: {str(e)}"
        logger.critical(f"[{api_name}] {error_message}")
        log = crud.create_log(
            db, api_name, url, None, None, False, error_message
        )
        return log.to_dict()


def run_all_checks() -> None:
    """
    Loops through every API defined in sample_apis.json and checks each
    one. This is the single function the scheduler triggers every
    CHECK_INTERVAL_SECONDS.

    Opens one database session for the whole batch (more efficient than
    one session per API) and always closes it, even if a check fails.
    """
    if not MONITORED_APIS:
        logger.warning("No APIs configured to monitor. Check sample_apis.json.")
        return

    db = SessionLocal()
    try:
        logger.info(f"Starting scheduled check of {len(MONITORED_APIS)} API(s)...")
        for api in MONITORED_APIS:
            check_api(db, api["name"], api["url"])
        logger.info("Scheduled check complete.")
    finally:
        db.close()


if __name__ == "__main__":
    # Allows running `python -m backend.monitor` manually to test checks
    # without starting the full FastAPI app or scheduler.
    from backend.database import init_db

    init_db()
    run_all_checks()
