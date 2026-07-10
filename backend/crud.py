"""
crud.py
-------
CRUD = Create, Read, Update, Delete. This file is the ONLY place in the
app that directly queries the database. Every other module (monitor.py,
main.py) calls functions from here instead of writing raw SQLAlchemy
queries themselves. This keeps database logic centralized and easy to
change later (e.g. swapping SQLite for PostgreSQL would only touch
database.py + this file).
"""

from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models import MonitoringLog
from backend.utils import calculate_uptime_percent, calculate_average
from backend.logger import get_logger

logger = get_logger(__name__)


def create_log(
    db: Session,
    api_name: str,
    url: str,
    status_code: Optional[int],
    response_time_ms: Optional[float],
    is_success: bool,
    error_message: Optional[str] = None,
) -> MonitoringLog:
    """
    Inserts one new monitoring result row into the database.
    Called once per API, per scheduled check (every 60s).
    """
    log_entry = MonitoringLog(
        api_name=api_name,
        url=url,
        status_code=status_code,
        response_time_ms=response_time_ms,
        is_success=is_success,
        error_message=error_message,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)  # populate auto-generated fields like id, timestamp
    return log_entry


def get_logs(
    db: Session,
    api_name: Optional[str] = None,
    limit: int = 200,
) -> list[MonitoringLog]:
    """
    Returns the most recent monitoring logs, newest first.

    Args:
        api_name: if provided, filters results to just that API.
        limit: max number of rows to return (prevents huge payloads).
    """
    query = db.query(MonitoringLog)
    if api_name:
        query = query.filter(MonitoringLog.api_name == api_name)
    return query.order_by(desc(MonitoringLog.timestamp)).limit(limit).all()


def get_latest_log_for_api(db: Session, api_name: str) -> Optional[MonitoringLog]:
    """Returns the single most recent check result for one API, or None."""
    return (
        db.query(MonitoringLog)
        .filter(MonitoringLog.api_name == api_name)
        .order_by(desc(MonitoringLog.timestamp))
        .first()
    )


def get_stats_for_api(db: Session, api_name: str, url: str) -> dict:
    """
    Computes aggregated statistics for one API:
    uptime %, average response time, last status, last checked time.

    This is what powers the "metric cards" on the Streamlit dashboard.
    """
    all_logs = (
        db.query(MonitoringLog).filter(MonitoringLog.api_name == api_name).all()
    )

    total_checks = len(all_logs)
    successful_checks = sum(1 for log in all_logs if log.is_success)
    response_times = [log.response_time_ms for log in all_logs if log.response_time_ms]

    latest = get_latest_log_for_api(db, api_name)

    return {
        "api_name": api_name,
        "url": url,
        "uptime_percent": calculate_uptime_percent(total_checks, successful_checks),
        "average_response_time_ms": calculate_average(response_times),
        "last_status_code": latest.status_code if latest else None,
        "last_checked": latest.timestamp.isoformat() if latest else None,
        "last_success": latest.is_success if latest else None,
        "total_checks": total_checks,
    }


def get_all_stats(db: Session, monitored_apis: list[dict]) -> list[dict]:
    """
    Convenience wrapper: computes stats for every API defined in
    sample_apis.json, in one call. Used by the /stats endpoint.
    """
    return [
        get_stats_for_api(db, api["name"], api["url"]) for api in monitored_apis
    ]


def export_logs_to_csv(db: Session, filepath: str, api_name: Optional[str] = None) -> str:
    """
    Exports monitoring logs to a CSV file using pandas.

    Args:
        filepath: full path where the CSV should be written.
        api_name: optional filter to export logs for just one API.

    Returns:
        The filepath that was written to (so the caller can confirm/serve it).
    """
    logs = get_logs(db, api_name=api_name, limit=100_000)  # effectively "all"
    records = [log.to_dict() for log in logs]

    # Even with zero rows, we still want a valid CSV with headers,
    # so the dashboard's download button never breaks.
    df = pd.DataFrame(
        records,
        columns=[
            "id",
            "api_name",
            "url",
            "timestamp",
            "status_code",
            "response_time_ms",
            "is_success",
            "error_message",
        ],
    )
    df.to_csv(filepath, index=False)
    logger.info(f"Exported {len(df)} log rows to {filepath}")
    return filepath
