"""
scheduler.py
------------
Wraps APScheduler to run monitor.run_all_checks() automatically every
CHECK_INTERVAL_SECONDS (default 60s), in the background, without
blocking the FastAPI app.

Why APScheduler (and not a while-loop with time.sleep):
A plain loop would block FastAPI from handling requests at the same
time. APScheduler's BackgroundScheduler runs jobs on a separate thread,
so the API and dashboard stay responsive while checks happen silently
in the background.
"""

from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import CHECK_INTERVAL_SECONDS
from backend.monitor import run_all_checks
from backend.logger import get_logger

logger = get_logger(__name__)

# Module-level scheduler instance so start/stop can be controlled
# from main.py's startup/shutdown events.
scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """
    Registers the monitoring job and starts the background scheduler.
    Safe to call once at application startup.
    """
    if scheduler.running:
        logger.info("Scheduler already running, skipping re-start.")
        return

    scheduler.add_job(
        run_all_checks,
        trigger="interval",
        seconds=CHECK_INTERVAL_SECONDS,
        id="api_monitoring_job",
        next_run_time=None,  # let APScheduler wait one interval before first run
        replace_existing=True,
    )

    # Run one check immediately on startup so the dashboard has data
    # right away instead of waiting a full 60 seconds.
    run_all_checks()

    scheduler.start()
    logger.info(
        f"Scheduler started: checking APIs every {CHECK_INTERVAL_SECONDS} seconds."
    )


def stop_scheduler() -> None:
    """Gracefully shuts down the scheduler (called on app shutdown)."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
