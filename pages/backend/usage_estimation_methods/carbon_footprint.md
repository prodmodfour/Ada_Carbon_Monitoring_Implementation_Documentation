---
title: Carbon Footprint
parent: Usage Estimation
nav_order: 2
---


# How we estimate Carbon Footprint

1. **Estimate electricity use (kWh).**
   Given total CPU time (in seconds) and the CPU’s TDP (watts), you compute energy as:
   `usage_kwh = cpu_seconds_total * cpu_tdp_w / (3600 * 1000)`.
   This is implemented in `estimate_electricity_usage_kwh(...)`. 

2. **Fetch carbon intensity (gCO₂e/kWh).**
   For a given hour starting at `start`, you query the UK Carbon Intensity API for the two half-hour windows, then average the `"actual"` values:

* Endpoint base: `https://api.carbonintensity.org.uk/intensity`
* Time format: ISO 8601 like `YYYY-MM-DDTHH:MMZ`
* You build two URLs (`start→start+30m`, `start+30m→start+60m`) and return the mean of both `actual` intensities. If the API call or parsing fails, the function returns `0`. 

3. **Calculate carbon footprint (grams CO₂e).**
   Multiply the estimated energy by the intensity:
   `carbon_footprint_g = usage_kwh * ci_g_per_kwh`.
   This is implemented in `estimate_carbon_footprint_gCO2eq(...)`. 

# Worked example

* Suppose the task used **7,200 CPU-seconds** on a **65 W** CPU.
  `usage_kwh = 7,200 * 65 / 3,600,000 = 0.13 kWh`.
* If the hour’s average carbon intensity is **150 gCO₂e/kWh**, then:
  `footprint = 0.13 * 150 = 19.5 gCO₂e`.

