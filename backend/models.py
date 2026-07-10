"""
models.py
---------
Defines the database schema using SQLAlchemy's ORM (Object-Relational
Mapping). Each class here becomes a table, and each attribute becomes
a column. This means we write Python classes instead of raw SQL.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime

from backend.database import Base


class MonitoringLog(Base):
    """
    One row = one API health check result.

    Columns:
        id             - auto-incrementing primary key
        api_name       - friendly name, e.g. "GitHub API"
        url            - the endpoint that was checked
        timestamp      - when the check happened (UTC)
        status_code    - HTTP status code returned (nullable if request
                         never completed, e.g. connection error)
        response_time_ms - how long the request took, in milliseconds
        is_success     - True if the API responded with a 2xx/3xx status
                         within the timeout window
        error_message  - human-readable error (timeout, connection error,
                         invalid URL, etc.), empty string if none
    """

    __tablename__ = "monitoring_logs"

    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_success = Column(Boolean, nullable=False, default=False)
    error_message = Column(String, nullable=True)

    def to_dict(self) -> dict:
        """
        Converts a row into a plain dictionary. Useful because FastAPI
        can return dictionaries as JSON directly, and it avoids leaking
        internal SQLAlchemy objects to the API layer.
        """
        return {
            "id": self.id,
            "api_name": self.api_name,
            "url": self.url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "is_success": self.is_success,
            "error_message": self.error_message,
        }
