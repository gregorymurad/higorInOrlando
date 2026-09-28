# 🎢 Park Quest

A personalized Universal Orlando wait-time dashboard for Epic Universe, Islands of Adventure, and Universal Studios Florida.

## Features

- Live attraction wait times from Queue-Times
- Open/closed ride status
- Attraction grouping by land
- Multi-select list of the rides you want to visit
- Personalized suggested ride order
- Current total queue-time estimate
- Low/moderate/high wait indicators
- Automatic API caching for ~4 minutes
- Park-specific local time
- Queue-Times attribution required by their API terms

## Run locally

### 1. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Streamlit

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit.

## Deploy

This can be deployed to Streamlit Community Cloud or another Python hosting service.

## Important API note

Queue-Times' real-time API is free but requires prominent attribution with a link to Queue-Times. Their live data is updated approximately every five minutes.

API documentation:
https://queue-times.com/en-US/pages/api

## About the recommendation engine

The current version intentionally uses an interpretable optimization heuristic rather than pretending to have a predictive ML model. It considers:

1. Current wait time
2. Very high-demand attractions
3. User preference for headliners vs. short waits
4. Grouping rides by land to reduce unnecessary backtracking

A future version could add historical wait-time prediction, weather, park hours, and estimated walking time.
