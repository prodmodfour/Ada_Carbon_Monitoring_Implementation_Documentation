---
title: Electricity
parent: Usage Estimation
nav_order: 1
---

# Todo
* Add justification for methods and values

# Estimating electricity usage from CPU usage

## Scope & inputs

We don’t have direct power telemetry or fine-grained utilisation. We **only** have:

* `busy_cpu_seconds`: total CPU-seconds a CPU core spent “busy” 
* `idle_cpu_seconds`: total CPU-seconds a CPU core spent “idle” 

Assume each vCPU ≈ one “CPU core” for accounting purposes.

## Assumptions

* Busy core power: **12 W**
* Idle core power: **1 W**

## Formula


Convert watt-seconds to kWh:

[
\text{kWh} ;=; \frac{12 \cdot \text{busy_cpu_seconds} ;+; 1 \cdot \text{idle_cpu_seconds}}{3600 \cdot 1000}
]

This multiplies time in seconds by an average per-core power for each state, sums to watt-seconds (joules), then divides by (3{,}600{,}000) to get kWh.

This is implemented as:

```python
usage_kwh = cpu_seconds_total * cpu_tdp_w / (3600 * 1000)
```


## Example

Suppose over a reporting window:

* `busy_cpu_seconds` = 18,000 s
* `idle_cpu_seconds` = 54,000 s

Energy (busy/idle method):
[
\frac{12\times 18{,}000 + 1\times 54{,}000}{3{,}600{,}000}
= \frac{270{,}000}{3{,}600{,}000}
= 0.075 \text{ kWh}
]

