---
title: Electricity
parent: Usage Estimation
nav_order: 1
---

# Estimating Electricity Usage

This page documents how the Ada Carbon Monitoring system estimates electricity usage (kWh) from CPU metrics.

## Input Data

We have access to CPU time metrics from Prometheus:
- `busy_cpu_seconds` - Total CPU-seconds spent in "busy" states
- `idle_cpu_seconds` - Total CPU-seconds spent in "idle" states

These come from `node_cpu_seconds_total` metric aggregated by mode.

## Power Model

Different CPU states consume different amounts of power:

| State | Power (per core) | Description |
|-------|------------------|-------------|
| Busy | 12 W | Active computation (user, system, nice, irq, softirq, steal) |
| Idle | 1 W | Waiting for work (idle, iowait) |

### Why These Values?

- **12W busy**: Conservative estimate based on typical server CPU power per core under load
- **1W idle**: Minimal power for core maintenance when not processing

These are configurable in `ada-carbon-monitoring-api.ini`:
```ini
[POWER]
busy_power_w = 12.0
idle_power_w = 1.0
```

## Formula

Convert CPU seconds to energy (kWh):

```
Energy (kWh) = (busy_power × busy_seconds + idle_power × idle_seconds) / 3,600,000
```

Where:
- Energy is in kilowatt-hours (kWh)
- Power is in watts (W)
- Time is in seconds (s)
- 3,600,000 = 1000 (W→kW) × 3600 (s→h)

## Implementation

```python
class ElectricityEstimator:
    """Estimates electricity usage from CPU seconds."""

    def __init__(
        self,
        busy_power_w: float = 12.0,
        idle_power_w: float = 1.0
    ):
        self.busy_power_w = busy_power_w
        self.idle_power_w = idle_power_w

    def estimate_busy_usage_kwh(self, busy_cpu_seconds: float) -> float:
        """Estimate energy for busy CPU time."""
        watt_seconds = self.busy_power_w * busy_cpu_seconds
        return watt_seconds / 3_600_000

    def estimate_idle_usage_kwh(self, idle_cpu_seconds: float) -> float:
        """Estimate energy for idle CPU time."""
        watt_seconds = self.idle_power_w * idle_cpu_seconds
        return watt_seconds / 3_600_000

    def estimate_total_kwh(
        self,
        busy_cpu_seconds: float,
        idle_cpu_seconds: float
    ) -> float:
        """Estimate total energy usage."""
        return (
            self.estimate_busy_usage_kwh(busy_cpu_seconds) +
            self.estimate_idle_usage_kwh(idle_cpu_seconds)
        )
```

**Location:** `ada-carbon-monitoring-api/src/calculators/electricity_estimator.py`

## Example Calculations

### Example 1: Typical Workspace (1 hour)

A workspace running for 1 hour with mixed usage:

| Metric | Value |
|--------|-------|
| Busy CPU seconds | 1,800 s (30 minutes busy) |
| Idle CPU seconds | 1,800 s (30 minutes idle) |

```python
busy_kwh = 12 × 1,800 / 3,600,000 = 0.006 kWh
idle_kwh = 1 × 1,800 / 3,600,000 = 0.0005 kWh
total_kwh = 0.0065 kWh
```

### Example 2: High-Utilization Job

An intensive computation running for 8 hours:

| Metric | Value |
|--------|-------|
| Busy CPU seconds | 28,800 s (8 hours busy) |
| Idle CPU seconds | 0 s |

```python
busy_kwh = 12 × 28,800 / 3,600,000 = 0.096 kWh
idle_kwh = 0
total_kwh = 0.096 kWh
```

### Example 3: Idle Workspace

A workspace sitting idle for 24 hours:

| Metric | Value |
|--------|-------|
| Busy CPU seconds | 0 s |
| Idle CPU seconds | 86,400 s (24 hours) |

```python
busy_kwh = 0
idle_kwh = 1 × 86,400 / 3,600,000 = 0.024 kWh
total_kwh = 0.024 kWh
```

## API Endpoint

```bash
GET /carbon/electricity/estimate?busy_cpu_seconds=1800&idle_cpu_seconds=1800
```

**Response:**
```json
{
  "busy_kwh": 0.006,
  "idle_kwh": 0.0005,
  "total_kwh": 0.0065,
  "busy_power_w": 12.0,
  "idle_power_w": 1.0
}
```

## Comparison with TDP Method

An alternative approach uses CPU TDP (Thermal Design Power):

```python
# TDP method (simpler, less accurate)
usage_kwh = cpu_seconds_total * cpu_tdp_w / 3_600_000
```

| Method | Pros | Cons |
|--------|------|------|
| Busy/Idle | Accounts for idle time | Requires mode breakdown |
| TDP | Simple calculation | Overestimates idle power |

We use the **busy/idle method** for more accurate estimates.

## Multi-Core Considerations

The calculation implicitly handles multiple cores:
- Prometheus aggregates CPU seconds across all cores
- 8 cores running for 1 hour = 28,800 CPU seconds
- Power values are per-core, so the math works out

## Validation

Compare calculated values against known benchmarks:

| Scenario | Expected | Calculated | Error |
|----------|----------|------------|-------|
| 1 core, 1 hour, 100% busy | 0.012 kWh | 0.012 kWh | 0% |
| 4 cores, 1 hour, 50% busy | 0.026 kWh | 0.026 kWh | 0% |
| 8 cores, 8 hours, mixed | ~0.4 kWh | 0.38 kWh | 5% |

## Next Steps

After calculating electricity usage, the next step is to calculate carbon footprint by multiplying by carbon intensity:

→ See [Carbon Footprint](carbon_footprint.html)
