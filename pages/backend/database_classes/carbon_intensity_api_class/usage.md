---
title: Usage
parent: Carbon Intensity API Request Class
nav_order: 2
---

# Usage

## For a specific UTC hour

```python
from datetime import datetime, timezone
client = CarbonIntensityAPIClient()

# e.g., 23 Sept 2025 17:00 UTC
start = datetime(2025, 9, 23, 17, 0, tzinfo=timezone.utc)
avg = client.get_carbon_intensity(start)
print("Average gCO2/kWh:", avg)
```

## “Right now” in London (rounded to the top of the current hour)

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

client = CarbonIntensityAPIClient()

# Current time in London, rounded down to the start of the hour
now_ldn = datetime.now(ZoneInfo("Europe/London"))
start_ldn_hour = now_ldn.replace(minute=0, second=0, microsecond=0)

# Convert to UTC (API uses Z/UTC)
start_utc = start_ldn_hour.astimezone(timezone.utc)

avg = client.get_carbon_intensity(start_utc)

# Your method returns 0 on error (despite the float|None hint), so handle that if you like:
if avg == 0:
    print("No data / API error")
else:
    print("Average gCO2/kWh:", avg)
```

## Fetch several consecutive hours (starting next full hour)

```python
from datetime import datetime, timedelta, timezone

client = CarbonIntensityAPIClient()

now_utc = datetime.now(timezone.utc)
next_full_hour = (now_utc.replace(minute=0, second=0, microsecond=0)
                  + timedelta(hours=1))

hours = 4  # how many hours to fetch
results = []
for i in range(hours):
    start = next_full_hour + timedelta(hours=i)
    avg = client.get_carbon_intensity(start)
    results.append((start.isoformat(), avg))

for when, val in results:
    print(when, "→", val, "gCO2/kWh")
```

### Tip

> The API expects boundaries on the half-hour (…:00 or …:30). Make sure the `start` you pass is aligned to `:00` or `:30` and is UTC (the `Z` in your URL).
