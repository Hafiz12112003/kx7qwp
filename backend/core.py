import glob
import json
import os
from bisect import bisect_right
from datetime import date, datetime, timedelta
from math import ceil, sqrt

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MONTH_START = date(2026, 1, 1)
MONTH_END = date(2026, 1, 31)

_FORECASTS = None  # start_time -> (publish_times, generations), sorted by publish time
_ACTUALS = None  # start_time -> generation


def _load(pattern):
    rows = []
    for p in sorted(glob.glob(os.path.join(DATA_DIR, pattern))):
        with open(p) as f:
            rows.extend(json.load(f))
    return rows


def _data():
    global _FORECASTS, _ACTUALS
    if _FORECASTS is None:
        tmp = {}
        for r in _load("windfor_*.json"):
            tmp.setdefault(r["startTime"], []).append((r["publishTime"], r["generation"]))
        _FORECASTS = {}
        for k, v in tmp.items():
            v.sort()
            _FORECASTS[k] = ([x[0] for x in v], [x[1] for x in v])
        _ACTUALS = {
            r["startTime"]: r["generation"]
            for r in _load("fuelhh_wind_*.json")
            if r["fuelType"] == "WIND"
        }
    return _FORECASTS, _ACTUALS


def _parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def cutoff_for(day, cutoff_hour):
    """Decision cutoff: cutoff_hour on D-1 (January: UK time = UTC)."""
    return f"{day - timedelta(days=1)}T{cutoff_hour:02d}:00:00Z"


def pick_forecast(start_time, cutoff):
    """Latest forecast for start_time published at or before cutoff.
    Forecasts are hourly, actuals half-hourly: HH:30 uses the HH:00 forecast."""
    fc, _ = _data()
    series = fc.get(start_time) or fc.get(start_time[:14] + "00:00Z")
    if not series:
        return None
    pubs, gens = series
    i = bisect_right(pubs, cutoff)
    if i == 0:
        return None
    return pubs[i - 1], gens[i - 1]


def day_points(day, cutoff_hour=9):
    _, actuals = _data()
    cutoff = cutoff_for(day, cutoff_hour)
    out = []
    for h in range(24):
        for m in (0, 30):
            t = f"{day}T{h:02d}:{m:02d}:00Z"
            actual = actuals.get(t)
            picked = pick_forecast(t, cutoff)
            if actual is None or picked is None:
                continue
            out.append(
                {
                    "time": t,
                    "forecast": picked[1],
                    "actual": actual,
                    "error": picked[1] - actual,
                    "publishTime": picked[0],
                }
            )
    return out


def _pct(sorted_vals, p):
    k = max(0, ceil(p / 100 * len(sorted_vals)) - 1)
    return sorted_vals[k]


def _stats(points):
    n = len(points)
    if n == 0:
        return {"n": 0}
    errs = [p["error"] for p in points]
    acts = [p["actual"] for p in points]
    abs_s = sorted(abs(e) for e in errs)
    err_s = sorted(errs)
    mean_actual = sum(acts) / n
    mae = sum(abs_s) / n
    pct = [abs(p["error"]) / p["actual"] * 100 for p in points if p["actual"] > 0]
    return {
        "n": n,
        "mean_actual": round(mean_actual),
        "mae": round(mae),
        "mae_pct": round(mae / mean_actual * 100, 1) if mean_actual else None,
        "rmse": round(sqrt(sum(e * e for e in errs) / n)),
        "bias": round(sum(errs) / n),
        "mape": round(sum(pct) / len(pct), 1) if pct else None,
        "abs_p50": _pct(abs_s, 50),
        "abs_p90": _pct(abs_s, 90),
        "abs_p99": _pct(abs_s, 99),
        "err_p10": _pct(err_s, 10),
        "err_p50": _pct(err_s, 50),
        "err_p90": _pct(err_s, 90),
    }


def accuracy(cutoff_hour=9, start=MONTH_START, end=MONTH_END):
    pts = []
    d = start
    while d <= end:
        pts.extend(day_points(d, cutoff_hour))
        d += timedelta(days=1)
    by_day, by_hour = {}, {}
    for p in pts:
        by_day.setdefault(p["time"][:10], []).append(p)
        by_hour.setdefault(int(p["time"][11:13]), []).append(p)
    return {
        "cutoff_hour": cutoff_hour,
        "summary": _stats(pts),
        "daily": [{"date": k, **_stats(v)} for k, v in sorted(by_day.items())],
        "hourly": [{"hour": k, **_stats(v)} for k, v in sorted(by_hour.items())],
    }


def horizon_breakdown(bucket_hours=6):
    """Error by forecast horizon (hours between publishTime and startTime),
    over every published forecast with a matching actual in January."""
    fc, actuals = _data()
    buckets = {}
    for start_time, (pubs, gens) in fc.items():
        if not start_time.startswith("2026-01") or start_time not in actuals:
            continue
        actual = actuals[start_time]
        st = _parse(start_time)
        for pub, gen in zip(pubs, gens):
            horizon = (st - _parse(pub)).total_seconds() / 3600
            if horizon < 0:
                continue
            b = int(horizon // bucket_hours) * bucket_hours
            buckets.setdefault(b, []).append({"actual": actual, "error": gen - actual})
    return [
        {"horizon": f"{b}-{b + bucket_hours}h", **_stats(v)}
        for b, v in sorted(buckets.items())
    ]


if __name__ == "__main__":
    print(json.dumps(accuracy()["summary"], indent=2))
    print("horizon buckets:")
    for row in horizon_breakdown():
        print(row["horizon"], "n", row["n"], "MAE", row["mae"], "bias", row["bias"])
    print("daily bias:", [d["bias"] for d in accuracy()["daily"]])
