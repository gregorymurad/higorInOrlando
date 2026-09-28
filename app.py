import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Higor in Orlando",
    page_icon="🎢",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://queue-times.com"
PARKS = {
    "🌌 Epic Universe": {"id": 334, "tz": "America/New_York"},
    "🦖 Islands of Adventure": {"id": 64, "tz": "America/New_York"},
    "🎬 Universal Studios Florida": {"id": 65, "tz": "America/New_York"},
}

st.markdown("""
<style>
    .hero {
        padding: 1.6rem 1.8rem;
        border-radius: 22px;
        background: linear-gradient(135deg, #111827, #312e81, #0f766e);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 { margin: 0; font-size: 2.6rem; }
    .hero p { margin: .45rem 0 0; opacity: .9; font-size: 1.05rem; }
    .metric-card {
        padding: 1rem;
        border-radius: 16px;
        border: 1px solid rgba(128,128,128,.25);
        text-align: center;
    }
    .small { opacity: .7; font-size: .85rem; }
    .wait-good { color: #16a34a; font-weight: 700; }
    .wait-mid { color: #d97706; font-weight: 700; }
    .wait-high { color: #dc2626; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🎢 Higor in Orlando</h1>
<p>Estrategista do Higor Miranda para os parques da Universal Orlando.</p>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=240, show_spinner=False)
def fetch_park(park_id):
    """
    Fetch Queue-Times live JSON with retries.

    Queue-Times updates its real-time feed approximately every 5 minutes.
    The slightly longer timeout/retry strategy is intentional because hosted
    Streamlit servers can occasionally have slower outbound connections.
    """
    url = f"{API_BASE}/parks/{park_id}/queue_times.json"

    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))

    headers = {
        "User-Agent": "ParkQuest/1.0 (Streamlit; Queue-Times API client)",
        "Accept": "application/json",
        "Connection": "keep-alive",
    }

    last_error = None
    for attempt in range(3):
        try:
            response = session.get(
                url,
                headers=headers,
                timeout=(10, 45),
            )
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Queue-Times returned an unexpected response format.")

            return data

        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(
        f"Queue-Times could not be reached after 3 attempts: {last_error}"
    )

def flatten(data):
    rows = []
    for land in data.get("lands", []):
        for ride in land.get("rides", []):
            rows.append({
                "land": land.get("name", "Other"),
                "ride": ride.get("name", "Unknown"),
                "is_open": bool(ride.get("is_open", False)),
                "wait": int(ride.get("wait_time", 0) or 0),
                "updated": ride.get("last_updated"),
            })
    # Some API responses may also expose rides outside lands.
    for ride in data.get("rides", []):
        rows.append({
            "land": "Other",
            "ride": ride.get("name", "Unknown"),
            "is_open": bool(ride.get("is_open", False)),
            "wait": int(ride.get("wait_time", 0) or 0),
            "updated": ride.get("last_updated"),
        })
    return pd.DataFrame(rows)

def wait_label(minutes, is_open):
    if not is_open:
        return "🔒 Closed"
    if minutes <= 15:
        return f"🟢 {minutes} min"
    if minutes <= 35:
        return f"🟡 {minutes} min"
    if minutes <= 60:
        return f"🟠 {minutes} min"
    return f"🔴 {minutes} min"

def recommendation_score(row, selected, land_order):
    # Transparent heuristic, not a black-box prediction.
    wait = row["wait"]
    urgency = 0
    if wait >= 60:
        urgency = 20
    elif wait >= 40:
        urgency = 10
    elif wait <= 20:
        urgency = 15

    # Prefer a short wait, but give very high-wait headliners an early-day priority.
    wait_score = max(0, 70 - wait)
    land_penalty = land_order.get(row["land"], 0) * 4
    return wait_score + urgency - land_penalty

with st.sidebar:
    st.header("🎟️ Plan your day")
    park_name = st.selectbox("Choose your park", list(PARKS.keys()))
    park = PARKS[park_name]

    st.divider()
    st.subheader("Your preferences")
    prioritize_headliners = st.toggle(
        "Prioritize big-ticket rides", value=True,
        help="Moves rides with historically/structurally long queues earlier."
    )
    avoid_long_waits = st.toggle(
        "Avoid very long waits", value=False,
        help="Favors rides currently below 35 minutes."
    )

    if st.button("🔄 Refresh live waits", width='stretch'):
        fetch_park.clear()
        st.rerun()

try:
    data = fetch_park(park["id"])
    df = flatten(data)
except Exception as e:
    st.error("🎢 Queue-Times is taking too long to respond.")
    st.warning(
        "The live feed is normally available, but the connection from the hosted "
        "app timed out. Park Quest automatically retries the request. "
        "You can also try the refresh button below."
    )
    if st.button("🔄 Try Queue-Times again", width='stretch'):
        fetch_park.clear()
        st.rerun()
    with st.expander("Technical details"):
        st.code(str(e))
    st.stop()

if df.empty:
    st.warning("No ride data is currently available for this park.")
    st.stop()

st.success("🟢 Live Queue-Times data connected", icon="🎢")

local_now = datetime.now(timezone.utc).astimezone(ZoneInfo(park["tz"]))
updated_values = pd.to_datetime(df["updated"], utc=True, errors="coerce")
latest = updated_values.max()

# Summary
open_rides = df[df["is_open"]]
avg_wait = round(open_rides["wait"].mean(), 1) if not open_rides.empty else 0
longest = open_rides.sort_values("wait", ascending=False).head(1)
shortest = open_rides.sort_values("wait", ascending=True).head(1)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Open attractions", f"{len(open_rides)}")
with c2:
    st.metric("Average wait", f"{avg_wait} min")
with c3:
    st.metric("Longest wait", f"{int(longest.iloc[0]['wait']) if not longest.empty else 0} min")
with c4:
    st.metric("Shortest wait", f"{int(shortest.iloc[0]['wait']) if not shortest.empty else 0} min")

st.caption(
    f"🕐 Local time: {local_now.strftime('%I:%M %p')}  •  "
    f"Live data refreshed about every 5 minutes by Queue-Times"
)

st.divider()

# Ride selection
st.subheader("⭐ Choose the rides you want to conquer")
st.write("Pick your must-do attractions and Park Quest will build an efficient order.")

all_rides = df["ride"].tolist()
selected = st.multiselect(
    "Your rides",
    options=all_rides,
    placeholder="Select your favorite rides...",
)

if selected:
    selected_df = df[df["ride"].isin(selected)].copy()

    st.markdown("### 🎯 Your selected rides")
    display = selected_df[["land", "ride", "is_open", "wait"]].copy()
    display["Status"] = [
        wait_label(w, o) for w, o in zip(display["wait"], display["is_open"])
    ]
    display = display.rename(columns={
        "land": "Land", "ride": "Attraction", "is_open": "Open", "wait": "Wait (min)"
    })
    st.dataframe(
        display[["Land", "Attraction", "Status", "Wait (min)", "Open"]],
        width='stretch',
        hide_index=True,
    )

    # A simple land-aware ordering. We estimate that grouping attractions
    # reduces walking/backtracking; current wait is the dominant factor.
    land_counts = selected_df["land"].value_counts()
    land_order = {land: i for i, land in enumerate(land_counts.index)}

    scores = []
    for _, row in selected_df.iterrows():
        score = recommendation_score(row, selected, land_order)
        if prioritize_headliners and row["wait"] >= 50:
            score += 18
        if avoid_long_waits:
            score += max(0, 40 - row["wait"])
        scores.append(score)

    selected_df["score"] = scores
    plan = selected_df.sort_values(["score", "wait"], ascending=[False, True]).reset_index(drop=True)

    st.divider()
    st.subheader("🧠 Suggested ride order")
    st.info(
        "This is an optimization heuristic, not a guarantee. It combines live wait time, "
        "priority for high-demand attractions, and land grouping to reduce unnecessary backtracking."
    )

    total_wait = int(plan["wait"].sum())
    p1, p2, p3 = st.columns(3)
    p1.metric("Selected attractions", len(plan))
    p2.metric("Current queue total", f"{total_wait} min")
    p3.metric("Approx. queue time", f"{total_wait / 60:.1f} hr")

    for i, row in plan.iterrows():
        wait = row["wait"]
        if not row["is_open"]:
            badge = "🔒 CLOSED"
        elif wait <= 20:
            badge = "🟢 LOW WAIT"
        elif wait <= 40:
            badge = "🟡 MODERATE"
        elif wait <= 60:
            badge = "🟠 HIGH"
        else:
            badge = "🔴 VERY HIGH"

        with st.container(border=True):
            a, b, c = st.columns([.7, 4.8, 1.5])
            with a:
                st.markdown(f"## {i+1}")
            with b:
                st.markdown(f"**{row['ride']}**")
                st.caption(f"{row['land']} • {badge}")
            with c:
                st.metric("Wait", f"{wait} min")

else:
    st.subheader("📊 Live attraction board")
    sort_choice = st.radio(
        "Sort by",
        ["Shortest wait", "Longest wait", "Land"],
        horizontal=True,
    )

    board = df.copy()
    if sort_choice == "Shortest wait":
        board = board.sort_values(["is_open", "wait"], ascending=[False, True])
    elif sort_choice == "Longest wait":
        board = board.sort_values(["is_open", "wait"], ascending=[False, False])
    else:
        board = board.sort_values(["land", "wait"])

    board["Status"] = [
        wait_label(w, o) for w, o in zip(board["wait"], board["is_open"])
    ]
    board = board.rename(columns={
        "land": "Land", "ride": "Attraction", "wait": "Wait (min)"
    })
    st.dataframe(
        board[["Land", "Attraction", "Status", "Wait (min)"]],
        width='stretch',
        hide_index=True,
    )

    st.info("👆 Select rides above to get a personalized order for your day.")

# Data freshness / attribution
st.divider()
st.markdown(
    "**Powered by [Queue-Times.com](https://queue-times.com/)** • "
    "Live wait times and ride status are supplied by Queue-Times."
)
st.caption(
    f"Last API timestamp observed: "
    f"{latest.strftime('%Y-%m-%d %H:%M UTC') if pd.notna(latest) else 'unknown'}"
)
