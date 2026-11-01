# UK Wind Forecast Monitor

Web app that helps a UK energy utility's day-ahead buying team (1) see the latest wind generation forecast available at decision time and (2) quantify how accurate those forecasts have been. Scope: January 2026, national wind only, Elexon BMRS data (WINDFOR forecasts, FUELHH actuals).

**Live app:** https://kx7qwp.vercel.app

## AI tool disclosure

This project was built with the help of an AI assistant (Claude by Anthropic) for planning, code generation and debugging. I reviewed, ran and tested all code.

## How the decision-time forecast is chosen

Purchases for delivery day D are made on D-1. For every half-hour target time in D, the app uses the latest forecast whose `publishTime` is at or before the cutoff on D-1 (default 09:00 UK time, adjustable in the UI). Forecasts later than the cutoff are ignored, so no information the buyer did not have is used. January is GMT, so UK time equals UTC.

WINDFOR is hourly and FUELHH is half-hourly, so the HH:30 target uses the forecast for HH:00.

## Metrics

Error = forecast - actual (positive = over-forecast). MAE, RMSE, bias, MAPE, absolute-error P50/P90/P99, signed-error percentiles, plus breakdowns by day and by forecast horizon. The "conservative" line on the chart is forecast minus the month's P90 over-forecast, computed in-sample on January data.

## Files and directories

- `backend/core.py` - data loading, decision-time forecast selection, accuracy metrics
- `backend/app.py` - Flask API (`/api/health`, `/api/accuracy`, `/api/horizon`, `/api/day`) and static file serving
- `backend/data/` - cached Elexon JSON (WINDFOR per publish day, FUELHH WIND per week)
- `backend/requirements.txt` - Python dependencies
- `frontend/` - React (Vite + Recharts) dashboard
- `fetch_data.py` - downloads the January data from the Elexon API into `backend/data/`
- `api/index.py`, `vercel.json`, `requirements.txt` - Vercel deployment
- `Dockerfile`, `.dockerignore` - single image: builds React, serves it with Flask via gunicorn

## How to start

### Docker

    docker build -t wind-forecast .
    docker run --rm -p 8000:8000 wind-forecast

Open http://localhost:8000

### Local development

Backend:

    python -m pip install -r backend/requirements.txt
    python backend/app.py

Frontend (second terminal):

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173 (Vite proxies `/api` to Flask on port 5000).

### Refresh the data (optional)

    python fetch_data.py

Run it from the repo root; then move or copy the resulting `data/` folder into `backend/data/`.

