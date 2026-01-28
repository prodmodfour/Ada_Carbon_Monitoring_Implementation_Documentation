---
title: Green Computing Basics
nav_order: 3
nav_exclude: false
---

# Green Computing Basics

This page covers the fundamental concepts behind carbon monitoring in computing systems.

## Key Variables

| Variable | Unit | Description |
|----------|------|-------------|
| Electricity Usage | kWh | Energy consumed by computing resources |
| Carbon Intensity | gCO2eq/kWh | Carbon emissions per unit of electricity |
| Carbon Footprint | gCO2eq | Total carbon emissions |

## Electricity Usage

Electricity usage measures the energy consumed by computing systems, typically in kilowatt-hours (kWh).

**How we measure it:**

In Ada, we estimate electricity from CPU time metrics:

```
Energy (kWh) = (busy_power x busy_seconds + idle_power x idle_seconds) / 3,600,000
```

Where:
- `busy_power` = 12W per core (active computation)
- `idle_power` = 1W per core (waiting for work)
- `busy_seconds` = CPU time in user, system, nice, irq, softirq, steal modes
- `idle_seconds` = CPU time in idle, iowait modes

## Carbon Intensity

Carbon intensity measures the grams of CO2 equivalent emitted per kilowatt-hour of electricity. It varies based on:

- **Time of day**: Lower at night, higher during peak demand
- **Weather**: Wind and solar generation vs fossil fuels
- **Season**: Heating demand affects generation mix

**UK Carbon Intensity Index:**

| Index | Range (gCO2/kWh) | Description |
|-------|------------------|-------------|
| Very Low | 0-50 | High renewable generation |
| Low | 50-100 | Good renewable mix |
| Moderate | 100-200 | Mixed generation |
| High | 200-300 | Higher fossil fuel use |
| Very High | 300+ | Peak demand, low renewables |

Ada uses the [UK Carbon Intensity API](https://carbonintensity.org.uk/) for real-time data, updated every 30 minutes.

## Carbon Footprint

Carbon footprint is the total carbon emissions, calculated as:

```
Carbon Footprint (gCO2eq) = Electricity Usage (kWh) x Carbon Intensity (gCO2/kWh)
```

**Example:**
- Electricity: 0.1 kWh
- Intensity: 150 gCO2/kWh
- Carbon: 0.1 x 150 = 15 gCO2eq

## Methods of Reducing Carbon Footprint

### Time Shifting

Schedule compute-intensive tasks during low carbon intensity periods.

The Ada carbon dashboard shows a forecast with the best 3-hour window highlighted, helping users choose optimal times for batch jobs.

**Example impact:**
- Same 0.1 kWh job at 3 AM (100 gCO2/kWh) = 10 gCO2eq
- Same job at 6 PM (250 gCO2/kWh) = 25 gCO2eq
- Savings: 60% reduction

### Reducing Overprovisioning

Allocate only the resources needed for a task.

Ada tracks CPU utilization (busy vs idle) to identify overprovisioned workspaces. A workspace with high idle time relative to busy time may be larger than needed.

### Cutting Down on Idle Usage

Keep resources powered on only when actively needed.

Ada distinguishes between:
- **Busy usage**: Active computation (12W per core)
- **Idle usage**: Waiting for work (1W per core)

The stacked bar charts show this breakdown, helping users identify workspaces that could be stopped when not in use.

## Carbon Equivalencies

To make carbon numbers relatable, we convert gCO2eq to real-world equivalencies:

| 1000 gCO2eq equals approximately... |
|-------------------------------------|
| 2.5 miles driven in a car |
| 17 tree-days of carbon absorption |
| 122 smartphone charges |
| 18 hours of HD video streaming |
| 14 liters of water boiled |

These equivalencies are displayed in the Ada carbon dashboard to help users understand their impact.
