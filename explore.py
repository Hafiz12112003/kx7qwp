import json
from collections import Counter

with open("windfor_sample.json") as f:
    data = json.load(f)

print("rows:", len(data))
print("first row:", data[0])
print("last row:", data[-1])

publish = sorted({r["publishTime"] for r in data})
start = sorted({r["startTime"] for r in data})

print("unique publishTimes:", len(publish))
print("publishTime range:", publish[0], "->", publish[-1])
print("unique startTimes:", len(start))
print("startTime range:", start[0], "->", start[-1])

per_publish = Counter(r["publishTime"] for r in data)
print("rows per publishTime (first 5):", list(per_publish.items())[:5])