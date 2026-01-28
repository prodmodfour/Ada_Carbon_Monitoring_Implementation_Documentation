---
title: Usage Estimation
parent: Backend
nav_order: 3
has_children: true
---

# Usage Estimation Methods

This section documents how the Ada Carbon Monitoring system estimates electricity usage and carbon footprint from CPU metrics.

## Overview

The carbon calculation pipeline:

```
CPU Metrics (Prometheus)
        │
        ▼
┌───────────────────────┐
│  Electricity          │
│  Estimation           │
│  (CPU → kWh)          │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Carbon Intensity     │
│  (UK Grid API)        │
│  (gCO2/kWh)           │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Carbon Footprint     │
│  (kWh × Intensity)    │
│  (gCO2eq)             │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│  Attribution          │
│  (User / Group)       │
└───────────────────────┘
```

## Key Concepts

### Busy vs Idle

CPU time is categorized as:
- **Busy**: Active computation (user, system, nice, irq, softirq, steal)
- **Idle**: Waiting for work (idle, iowait)

### Power Model

Different power consumption for each state:
- **Busy power**: 12W per CPU core
- **Idle power**: 1W per CPU core

### Carbon Intensity

UK grid carbon intensity varies throughout the day:
- **Low**: 50-100 gCO2/kWh (high renewable generation)
- **Moderate**: 100-200 gCO2/kWh (mixed generation)
- **High**: 200-300+ gCO2/kWh (high fossil fuel generation)

## Calculation Steps

### Step 1: Get CPU Metrics

Query Prometheus for CPU seconds:

```python
cpu_data = prometheus_client.get_cpu_usage_breakdown(
    timestamp=datetime.now(),
    cloud_project_name="IDAaaS",
    host="172.16.100.50"
)
# Returns: {"busy": 1234.5, "idle": 56789.0}
```

### Step 2: Estimate Electricity

Convert CPU seconds to kWh:

```python
energy_kwh = electricity_estimator.estimate_total_kwh(
    busy_seconds=cpu_data["busy"],
    idle_seconds=cpu_data["idle"]
)
# Formula: (12W × busy + 1W × idle) / 3,600,000
```

### Step 3: Get Carbon Intensity

Query UK Grid API:

```python
intensity = carbon_client.get_current_intensity()
# Returns: {"intensity": 185, "index": "moderate"}
```

### Step 4: Calculate Carbon

Multiply energy by intensity:

```python
carbon_gco2eq = energy_kwh * intensity["intensity"]
```

### Step 5: Attribute to User/Group

Match to workspace owner or facility:

```python
user = mongo_client.get_user_by_platform_name(workspace["owner"])
# Or for groups:
group = f"{cloud_project}_{machine_name}"
```

## Pages in This Section

| Page | Description |
|------|-------------|
| [Electricity](electricity.html) | Estimating kWh from CPU seconds |
| [Carbon Footprint](carbon_footprint.html) | Calculating gCO2eq from kWh |
| [User Attribution](user_attribution.html) | Attributing carbon to users |
| [Group Attribution](group_attribution.html) | Attributing carbon to groups |

## Implementation

The calculations are implemented in `ada-carbon-monitoring-api`:

| Module | Purpose |
|--------|---------|
| `src/calculators/electricity_estimator.py` | CPU → kWh conversion |
| `src/calculators/carbon_calculator.py` | kWh → gCO2eq conversion |
| `src/calculators/carbon_equivalency.py` | gCO2eq → equivalencies |
| `src/clients/prometheus_client.py` | CPU metric queries |
| `src/clients/carbon_intensity_client.py` | UK Grid API client |
| `src/models/workspace_tracker.py` | Orchestration and attribution |

## Example: Full Calculation

```python
from datetime import datetime
from src.models.workspace_tracker import WorkspaceTracker

# Initialize tracker
tracker = WorkspaceTracker(
    prometheus_url="https://prometheus.example.com",
    mongo_uri="mongodb://localhost:27017"
)

# Track a group
entry = tracker.track_group(
    cloud_project_name="IDAaaS",
    machine_name="Muon",
    timestamp=datetime.now()
)

print(f"CPU Time: {entry.busy_cpu_seconds_total + entry.idle_cpu_seconds_total:.1f} seconds")
print(f"Energy: {entry.total_usage_kwh:.4f} kWh")
print(f"Carbon: {entry.total_usage_gco2eq:.2f} gCO2eq")
print(f"Intensity: {entry.carbon_intensity_g_per_kwh:.0f} gCO2/kWh")
```

Output:
```
CPU Time: 287776.7 seconds
Energy: 0.0816 kWh
Carbon: 18.89 gCO2eq
Intensity: 232 gCO2/kWh
```
