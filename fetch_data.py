import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = "data"
os.makedirs(OUT, exist_ok=True)


def get_json(url, retries=5):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  retry {attempt + 1} after error: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def save(path, rows):
    with open(path, "w") as f:
        json.dump(rows, f)


# Forecasts: one request per publish day.
# Decisions for delivery days 1-31 Jan are made on 31 Dec - 30 Jan.
d = date(2025, 12, 30)
last = date(2026, 1, 30)
while d <= last:
    path = f"{OUT}/windfor_{d}.json"
    if os.path.exists(path):
        print("skip", path)
    else:
        nxt = d + timedelta(days=1)
        url = (
            f"{BASE}/WINDFOR/stream"
            f"?publishDateTimeFrom={d}T00:00:00Z&publishDateTimeTo={nxt}T00:00:00Z"
        )
        print("fetching", path)
        save(path, get_json(url))
    d += timedelta(days=1)

# Actuals: WIND only, one request per week.
d = date(2026, 1, 1)
end = date(2026, 1, 31)
while d <= end:
    to = min(d + timedelta(days=6), end)
    path = f"{OUT}/fuelhh_wind_{d}_{to}.json"
    if os.path.exists(path):
        print("skip", path)
    else:
        url = (
            f"{BASE}/FUELHH/stream"
            f"?settlementDateFrom={d}&settlementDateTo={to}&fuelType=WIND"
        )
        print("fetching", path)
        save(path, get_json(url))
    d = to + timedelta(days=1)

print("done")
