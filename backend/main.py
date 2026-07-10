"""
main.py
-------
The FastAPI backend. Its only job is to sit between the database and
the Streamlit dashboard: it starts the background scheduler on launch,
and exposes simple read endpoints that the dashboard calls over HTTP.

Per project requirements, FastAPI here is intentionally "just a
backend" — no auth, no complex routing, just clean read endpoints.
"""

import os
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import init_db, get_db
from backend.scheduler import start_scheduler, stop_scheduler
from backend.config import MONITORED_APIS, DATA_DIR
from backend.schemas import MonitoringLogSchema, APIStatsSchema, MonitoredAPISchema
from backend import crud
from backend.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="API Monitoring Dashboard - Backend",
    description="Serves monitoring data collected from public REST APIs.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    """
    Runs once when FastAPI starts:
    1. Creates database tables if they don't exist.
    2. Starts the background scheduler that checks APIs every 60s.
    """
    logger.info("Starting API Monitoring Dashboard backend...")
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """Gracefully stops the scheduler when the app is shut down."""
    stop_scheduler()
    logger.info("Backend shut down cleanly.")


@app.get("/", tags=["Health"])
def root():
    """Simple health check to confirm the backend is alive."""
    return {"status": "ok", "message": "API Monitoring Dashboard backend is running."}


@app.get("/apis", response_model=list[MonitoredAPISchema], tags=["Config"])
def list_monitored_apis():
    """Returns the list of APIs currently being monitored (from sample_apis.json)."""
    return MONITORED_APIS


@app.get("/logs", response_model=list[MonitoringLogSchema], tags=["Logs"])
def read_logs(
    api_name: str | None = Query(default=None, description="Filter by API name"),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """
    Returns recent monitoring log rows, newest first.
    Powers the "Monitoring Logs" table on the dashboard.
    """
    logs = crud.get_logs(db, api_name=api_name, limit=limit)
    return [MonitoringLogSchema(**log.to_dict()) for log in logs]


@app.get("/stats", response_model=list[APIStatsSchema], tags=["Stats"])
def read_stats(db: Session = Depends(get_db)):
    """
    Returns aggregated stats (uptime %, avg response time, last checked)
    for every monitored API. Powers the dashboard's metric cards.
    """
    if not MONITORED_APIS:
        raise HTTPException(status_code=404, detail="No APIs configured to monitor.")
    return crud.get_all_stats(db, MONITORED_APIS)


@app.get("/logs/export", tags=["Logs"])
def export_logs(
    api_name: str | None = Query(default=None, description="Filter by API name"),
    db: Session = Depends(get_db),
):
    """
    Exports monitoring logs to a CSV file and returns it as a download.
    Used by the "Export to CSV" button on the dashboard.
    """
    export_path = os.path.join(DATA_DIR, "exported_logs.csv")
    crud.export_logs_to_csv(db, export_path, api_name=api_name)
    return FileResponse(
        path=export_path,
        filename="monitoring_logs.csv",
        media_type="text/csv",
    )
