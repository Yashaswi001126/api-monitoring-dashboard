# 📡 API Monitoring Dashboard

A production-style monitoring tool that automatically checks the health of multiple public REST APIs every 60 seconds, stores the results in a database, and visualizes uptime, latency, and failures on a live dashboard.

Built to demonstrate practical skills in **backend engineering, automation, data pipelines, and observability tooling** — the kind of work involved in network/API monitoring systems.

---

## ✨ Features

- 🔁 Automatically checks multiple REST APIs every 60 seconds (via APScheduler)
- 🗄️ Records URL, timestamp, HTTP status code, response time, success/failure, and error messages in SQLite
- 📊 Live Streamlit dashboard with:
  - Real-time API status cards (🟢 UP / 🔴 DOWN)
  - Uptime % per API
  - Average response time per API
  - Response time trend chart (Plotly)
  - Success vs. Failure breakdown (Plotly)
  - Filterable monitoring logs table
  - Last checked timestamp
- 📥 One-click CSV export of monitoring logs
- 🧾 Persistent application logs (`logs/monitoring.log`)
- 🛡️ Graceful handling of invalid URLs, timeouts, and connection errors — a broken API never crashes the monitor

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI |
| Scheduler | APScheduler |
| ORM / Database | SQLAlchemy + SQLite |
| HTTP Client | Requests |
| Dashboard | Streamlit |
| Data Processing | Pandas |
| Charts | Plotly |

---

## 🏗️ Architecture

```
                 ┌───────────────────┐
                 │   sample_apis.json│
                 │ (APIs to monitor) │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
   every 60s     │   scheduler.py    │
  ───────────────►   (APScheduler)   │
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │    monitor.py     │  ← pings each API, times it,
                 │ (health checks)   │    catches timeouts/errors
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │     crud.py       │  ← writes results
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │  monitoring.db    │  (SQLite via SQLAlchemy)
                 └─────────┬─────────┘
                           ▼
                 ┌───────────────────┐
                 │     main.py       │  ← FastAPI: /apis /logs /stats
                 │  (FastAPI backend)│     /logs/export
                 └─────────┬─────────┘
                           │  HTTP requests
                           ▼
                 ┌───────────────────┐
                 │  dashboard/app.py │  ← Streamlit UI
                 │   (Streamlit UI)  │     (metrics, charts, tables)
                 └───────────────────┘
```

The scheduler runs **inside** the FastAPI process (started on app startup), so running one backend process handles both scheduled checks and API serving. Streamlit runs as a separate process and talks to FastAPI purely over HTTP — the two can be developed, restarted, or deployed independently.

---

## 📁 Project Structure

```
api-monitoring-dashboard/
├── backend/
│   ├── __init__.py
│   ├── config.py        # Settings: paths, intervals, loads sample_apis.json
│   ├── database.py       # SQLAlchemy engine + session setup
│   ├── models.py          # MonitoringLog ORM table definition
│   ├── schemas.py          # Pydantic request/response models
│   ├── logger.py            # Logging configuration (logs/monitoring.log)
│   ├── utils.py               # URL validation, uptime/average helpers
│   ├── crud.py                  # All database read/write operations
│   ├── monitor.py                 # Core API health-check logic
│   ├── scheduler.py                 # APScheduler background job
│   └── main.py                        # FastAPI app + endpoints
├── dashboard/
│   └── app.py             # Streamlit dashboard
├── data/                    # monitoring.db + exported CSVs (gitignored)
├── logs/                      # monitoring.log (gitignored)
├── sample_apis.json             # List of APIs to monitor
├── pyproject.toml                 # Makes the project pip-installable (see below)
├── requirements.txt
├── .gitignore
└── README.md
```

> **Note on package naming:** the backend package is named `backend`, not `app`. Naming a top-level package `app` is a common source of import collisions — it clashes with `app.py` entry-point filenames (as Streamlit uses here), Flask's conventional `app` variable, and other tools that reserve that name. `backend` avoids that entirely.

---

## ⚙️ Installation

**1. Clone the repository and enter the folder**
```bash
git clone <your-repo-url>
cd api-monitoring-dashboard
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Install the project itself in editable mode**
```bash
pip install -e .
```
This registers the `backend` package with your Python environment (pointing back at this source folder), so `backend.config`, `backend.main`, etc. are importable from any script or working directory — including when Streamlit runs `dashboard/app.py`. This is what lets both `uvicorn` and `streamlit` work correctly **without** manually exporting `PYTHONPATH`.

---

## ▶️ Running the Project

The backend and dashboard run as **two separate processes** — open two terminal windows (both with the virtual environment activated).

**Terminal 1 — Start the FastAPI backend** (this also starts the scheduler):
```bash
uvicorn backend.main:app --reload --port 8000
```
- API docs available at: http://127.0.0.1:8000/docs
- On startup, it immediately runs one check of all configured APIs, then repeats every 60 seconds.

**Terminal 2 — Start the Streamlit dashboard:**
```bash
streamlit run dashboard/app.py
```
- Dashboard opens at: http://localhost:8501

> ⚠️ Start the backend **first** — the dashboard fetches data from it over HTTP and will show a friendly warning if it can't connect.

---

## 🔧 Configuring Which APIs to Monitor

Edit `sample_apis.json` to add, remove, or change monitored endpoints:

```json
{
  "apis": [
    { "name": "GitHub API", "url": "https://api.github.com" },
    { "name": "JSONPlaceholder", "url": "https://jsonplaceholder.typicode.com/posts/1" }
  ]
}
```
Restart the backend after editing this file so it reloads the list.

---

## 🧪 Testing the Monitor Manually

You can run a single monitoring pass without starting FastAPI or Streamlit:
```bash
python -m backend.monitor
```
This creates the database (if needed), checks every configured API once, and prints results to the console and `logs/monitoring.log`.

---

## 🛡️ Error Handling

The monitor is designed to never crash, no matter what a target API does:

| Failure Type | Handling |
|---|---|
| Invalid URL format | Caught before any network call, logged as `Invalid URL` |
| Connection refused / DNS failure | Caught as `ConnectionError`, logged with details |
| Timeout | Caught after 5s, logged as `Request timed out` |
| Non-2xx/3xx HTTP status | Recorded as a failure with the status code |
| Any other unexpected error | Caught by a final safety-net handler |

---

## 📌 Possible Extensions

- Add email/Slack alerts when an API goes down
- Add authentication for a multi-user dashboard
- Move from SQLite to PostgreSQL for larger-scale deployments
- Containerize with Docker for easier deployment


---

## 📄 License

This project is open-source and free to use for learning and portfolio purposes.
