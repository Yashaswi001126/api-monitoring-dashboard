"""
dashboard/app.py
-----------------
The Streamlit frontend for the API Monitoring Dashboard.

This file ONLY talks to the FastAPI backend over HTTP (via `requests`)
— it never touches the database directly. That separation means the
dashboard and backend can be developed, tested, and even deployed
independently.

Run with:  streamlit run dashboard/app.py
(Requires the FastAPI backend to already be running on port 8000.)
"""

import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# NOTE ON IMPORTS:
# This works with a plain `streamlit run dashboard/app.py` — no sys.path
# hacks and no PYTHONPATH exports needed — because the project is
# installed as an editable package (see `pip install -e .` in the
# README). That registers `backend` as a real, importable Python
# package system-wide, the same way any pip-installed library works,
# regardless of which script or working directory imports it.
from backend.config import API_BASE_URL, CHECK_INTERVAL_SECONDS

# ---------------------------------------------------------------------------
# Page configuration — must be the first Streamlit command.
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="API Monitoring Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dark theme CSS.
#
# WHY `!important` IS EVERYWHERE BELOW:
# Streamlit wraps every st.markdown() HTML block (and especially content
# placed inside st.columns()) in its own container elements that carry
# default background/text-color rules. Those built-in rules have higher
# specificity than plain custom classes, so without `!important` they
# silently win — which is exactly what caused the white-on-white cards
# in the screenshot (your #1E293B backgrounds and white text were being
# rendered, then immediately overridden). `!important` guarantees our
# colors take priority. We also explicitly force the app's own background
# dark and neutralize Streamlit's wrapper backgrounds, so the app looks
# consistent regardless of the viewer's OS/browser light-mode setting.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Force the whole app dark, independent of system theme */
        .stApp {
            background-color: #0F172A !important;
        }

        /* Headings and body text used inside our custom HTML blocks */
        h1, h2, h3 { color: #F8FAFC !important; }
        p { color: #CBD5E1 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Backend API helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15)
def fetch_apis() -> list[dict]:
    """Fetches the list of monitored APIs from the backend (cached 15s)."""
    resp = requests.get(f"{API_BASE_URL}/apis", timeout=5)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=15)
def fetch_stats() -> list[dict]:
    """Fetches aggregated per-API stats (uptime %, avg response time)."""
    resp = requests.get(f"{API_BASE_URL}/stats", timeout=5)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=15)
def fetch_logs(api_name: str | None = None, limit: int = 500) -> list[dict]:
    """Fetches recent monitoring logs, optionally filtered by API name."""
    params = {"limit": limit}
    if api_name and api_name != "All APIs":
        params["api_name"] = api_name
    resp = requests.get(f"{API_BASE_URL}/logs", params=params, timeout=5)
    resp.raise_for_status()
    return resp.json()


def backend_is_reachable() -> bool:
    """Quick check so the dashboard shows a friendly message if the
    FastAPI backend isn't running yet, instead of a stack trace."""
    try:
        requests.get(f"{API_BASE_URL}/", timeout=3)
        return True
    except requests.exceptions.RequestException:
        return False


# ---------------------------------------------------------------------------
# Guard: if backend isn't running, stop here with a helpful message.
# ---------------------------------------------------------------------------
if not backend_is_reachable():
    st.error(
        "⚠️ Could not reach the FastAPI backend at "
        f"`{API_BASE_URL}`.\n\n"
        "Start it first with:\n\n"
        "```bash\nuvicorn backend.main:app --reload --port 8000\n```"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — controls
# ---------------------------------------------------------------------------
st.sidebar.title("📡 Controls")

if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    f"Backend checks each API every **{CHECK_INTERVAL_SECONDS} seconds**. "
    "Click Refresh Now to pull the latest results, or reload the page."
)

apis = fetch_apis()
api_names = ["All APIs"] + [api["name"] for api in apis]
selected_api = st.sidebar.selectbox("Filter by API", api_names)

st.sidebar.markdown("---")
st.sidebar.subheader("⬇️ Export Logs")
export_scope = None if selected_api == "All APIs" else selected_api
if st.sidebar.button("Download CSV", use_container_width=True):
    params = {"api_name": export_scope} if export_scope else {}
    csv_resp = requests.get(f"{API_BASE_URL}/logs/export", params=params, timeout=10)
    st.sidebar.download_button(
        label="✅ Click to Save monitoring_logs.csv",
        data=csv_resp.content,
        file_name="monitoring_logs.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Main header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="
        background-color:#1E293B;
        padding:20px;
        border-radius:12px;
        border:1px solid #334155;
        margin-bottom:20px;
    ">
        <h1 style="color:#F8FAFC !important; margin:0;">
            📡 API Monitoring Dashboard
        </h1>
        <p style="color:#CBD5E1 !important; margin-top:8px;">
            Live health monitoring for public REST APIs — status, uptime, and latency at a glance.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
stats = fetch_stats()
stats_df = pd.DataFrame(stats)
logs = fetch_logs(selected_api)
logs_df = pd.DataFrame(logs)

if not logs_df.empty:
    logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])

# ---------------------------------------------------------------------------
# Top-level KPI row
# ---------------------------------------------------------------------------
total_apis = len(stats_df)
overall_uptime = round(stats_df["uptime_percent"].mean(), 2) if not stats_df.empty else 0.0
overall_avg_response = (
    round(stats_df["average_response_time_ms"].mean(), 2) if not stats_df.empty else 0.0
)
last_checked = (
    pd.to_datetime(stats_df["last_checked"]).max()
    if not stats_df.empty and stats_df["last_checked"].notna().any()
    else None
)

CARD_CSS = """
<style>
    * { box-sizing: border-box; font-family: "Source Sans Pro", sans-serif; }
    body { margin: 0; background: transparent; }

    .status-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
    }
    .status-up { background-color: #d1f5e0; color: #0f7a3d; }
    .status-down { background-color: #fbdada; color: #b0261a; }

    .api-card {
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 10px;
        background-color: #1E293B;
        color: #F1F5F9;
    }

    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title { color: #CBD5E1; font-size: 16px; font-weight: 600; margin-bottom: 10px; }
    .metric-value { color: #F8FAFC; font-size: 34px; font-weight: 700; }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
    }
    .status-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
    }
    @media (max-width: 900px) {
        .metric-grid { grid-template-columns: repeat(2, 1fr); }
        .status-grid { grid-template-columns: 1fr; }
    }
</style>
"""


def render_html_card_block(inner_html: str, height: int) -> None:
    """
    Renders a block of custom-styled HTML inside an ISOLATED iframe via
    st.components.v1.html(), instead of st.markdown(unsafe_allow_html=True).

    WHY THIS WAS NECESSARY:
    Newer Streamlit versions have known, currently-open bugs (see
    streamlit/streamlit GitHub issues around unsafe_allow_html content
    getting an unremovable default background) where the frontend
    silently re-applies its own background styling to raw HTML markdown
    blocks, no matter what CSS — even with !important — is supplied.
    An <iframe> (which is what components.html renders into) is a
    completely separate document from Streamlit's page. Streamlit's own
    CSS physically cannot cross that boundary, so our colors are
    guaranteed to render exactly as written.
    """
    components.html(CARD_CSS + inner_html, height=height, scrolling=False)


# ---------------------------------------------------------------------------
# Top-level KPI metric cards
# ---------------------------------------------------------------------------
metrics = [
    ("📡 APIs Monitored", str(total_apis)),
    ("✅ Overall Uptime", f"{overall_uptime}%"),
    ("⚡ Avg Response Time", f"{overall_avg_response} ms"),
    (
        "🕒 Last Checked",
        last_checked.strftime("%H:%M:%S") if last_checked is not None else "—",
    ),
]
metric_cards_html = "".join(
    f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """
    for title, value in metrics
)
render_html_card_block(f'<div class="metric-grid">{metric_cards_html}</div>', height=140)

st.markdown("###")

# ---------------------------------------------------------------------------
# Per-API status cards
# ---------------------------------------------------------------------------
st.subheader("🔍 Live API Status")

if stats_df.empty:
    st.info("No stats available yet — waiting for the first scheduled check to complete.")
else:
    card_blocks = []
    for _, api_stat in stats_df.iterrows():
        is_up = bool(api_stat["last_success"])
        badge_class = "status-up" if is_up else "status-down"
        badge_text = "🟢 UP" if is_up else "🔴 DOWN"
        last_checked_str = (
            pd.to_datetime(api_stat["last_checked"]).strftime("%H:%M:%S")
            if pd.notna(api_stat["last_checked"])
            else "—"
        )
        card_blocks.append(
            f"""
            <div class="api-card">
                <b>{api_stat['api_name']}</b><br>
                <span class="status-badge {badge_class}">{badge_text}</span>
                <br><br>
                Uptime: <b>{api_stat['uptime_percent']}%</b><br>
                Avg Response: <b>{api_stat['average_response_time_ms']} ms</b><br>
                Last Checked: <b>{last_checked_str}</b>
            </div>
            """
        )
    num_rows = -(-len(card_blocks) // 3)  # ceiling division
    render_html_card_block(
        f'<div class="status-grid">{"".join(card_blocks)}</div>',
        height=num_rows * 190 + 20,
    )

st.markdown("###")


# ---------------------------------------------------------------------------
# Charts: Response Time Trend + Success vs Failure
# ---------------------------------------------------------------------------
chart_col1, chart_col2 = st.columns([2, 1])

with chart_col1:
    st.subheader("📈 Response Time Trend")
    if logs_df.empty:
        st.info("No log data yet.")
    else:
        trend_df = logs_df.sort_values("timestamp")
        fig = px.line(
            trend_df,
            x="timestamp",
            y="response_time_ms",
            color="api_name",
            markers=True,
            labels={
                "timestamp": "Time",
                "response_time_ms": "Response Time (ms)",
                "api_name": "API",
            },
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=380,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
        )
        st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    st.subheader("✅ Success vs ❌ Failure")
    if logs_df.empty:
        st.info("No log data yet.")
    else:
        outcome_counts = (
            logs_df["is_success"]
            .map({True: "Success", False: "Failure"})
            .value_counts()
            .reset_index()
        )
        outcome_counts.columns = ["Outcome", "Count"]
        fig2 = px.pie(
            outcome_counts,
            names="Outcome",
            values="Count",
            color="Outcome",
            color_discrete_map={"Success": "#0f7a3d", "Failure": "#b0261a"},
            hole=0.5,
        )
        fig2.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=380,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("###")

# ---------------------------------------------------------------------------
# Logs table
# ---------------------------------------------------------------------------
st.subheader("📋 Monitoring Logs")

if logs_df.empty:
    st.info("No logs recorded yet. Logs will appear here after the first check.")
else:
    display_df = logs_df.copy()
    display_df["Status"] = display_df["is_success"].map({True: "🟢 Success", False: "🔴 Failure"})
    display_df = display_df[
        ["timestamp", "api_name", "url", "status_code", "response_time_ms", "Status", "error_message"]
    ].rename(
        columns={
            "timestamp": "Timestamp",
            "api_name": "API",
            "url": "URL",
            "status_code": "HTTP Status",
            "response_time_ms": "Response Time (ms)",
            "error_message": "Error Message",
        }
    )
    st.dataframe(display_df, use_container_width=True, height=350)

