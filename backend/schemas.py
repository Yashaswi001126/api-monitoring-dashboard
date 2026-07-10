"""
schemas.py
----------
Pydantic models used by FastAPI to validate and document data going in
and out of the API. These are separate from models.py (the SQLAlchemy
database tables) on purpose: schemas.py describes the API "contract",
while models.py describes the database structure. Keeping them separate
is a standard FastAPI best practice.
"""

from typing import Optional
from pydantic import BaseModel


class MonitoringLogSchema(BaseModel):
    """Shape of a single monitoring log record returned by the API."""

    id: int
    api_name: str
    url: str
    timestamp: str
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    is_success: bool
    error_message: Optional[str] = None

    class Config:
        from_attributes = True  # allows creating this from ORM objects


class APIStatsSchema(BaseModel):
    """Aggregated stats for one monitored API (used for dashboard cards)."""

    api_name: str
    url: str
    uptime_percent: float
    average_response_time_ms: float
    last_status_code: Optional[int] = None
    last_checked: Optional[str] = None
    last_success: Optional[bool] = None
    total_checks: int


class MonitoredAPISchema(BaseModel):
    """Shape of an entry from sample_apis.json."""

    name: str
    url: str
