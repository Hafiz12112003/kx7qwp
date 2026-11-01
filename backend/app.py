import os
from datetime import date

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import core

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
CORS(app)


def _cutoff_hour():
    try:
        h = int(request.args.get("cutoff_hour", 9))
    except ValueError:
        return None
    return h if 0 <= h <= 23 else None


@app.get("/")
def index():
    if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
        return send_from_directory(STATIC_DIR, "index.html")
    return jsonify(message="API running. Use /api/health, /api/accuracy, /api/horizon, /api/day"), 200


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/accuracy")
def accuracy():
    h = _cutoff_hour()
    if h is None:
        return jsonify(error="cutoff_hour must be an integer 0-23"), 400
    return jsonify(core.accuracy(h))


@app.get("/api/horizon")
def horizon():
    return jsonify(core.horizon_breakdown())


@app.get("/api/day")
def day():
    h = _cutoff_hour()
    if h is None:
        return jsonify(error="cutoff_hour must be an integer 0-23"), 400
    try:
        d = date.fromisoformat(request.args.get("date", ""))
    except ValueError:
        return jsonify(error="date must be YYYY-MM-DD"), 400
    if not (core.MONTH_START <= d <= core.MONTH_END):
        return jsonify(error="date must be in January 2026"), 400
    pts = core.day_points(d, h)
    return jsonify(
        date=str(d),
        cutoff=core.cutoff_for(d, h),
        points=pts,
        summary=core._stats(pts),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
