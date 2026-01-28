---
title: Recording Rules
parent: Backend
nav_order: 4
---

# Prometheus Recording Rules

Recording rules pre-aggregate common queries so the carbon dashboard loads quickly. Without them, each API call runs expensive `increase()` queries across all time series in real time.

The rules file is at `prometheus-preprod/prometheus/recording_rules.yml` in ada-carbon-monitoring-api.

## Why Recording Rules?

The carbon monitoring API needs to calculate CPU usage over time periods (hourly, daily). The raw Prometheus query for this is:

```promql
sum by (cloud_project_name) (
  increase(node_cpu_seconds_total{mode!="idle", cloud_project_name="IDAaaS"}[1h])
)
```

This query scans every `node_cpu_seconds_total` sample in the last hour, computes the increase for each time series, filters by mode, and sums by project. With hundreds of machines and multiple CPU cores each, this is slow.

Recording rules run these queries on a schedule and store the results as new time series. The API then queries the pre-computed result directly:

```promql
ada:cpu_busy_seconds_increase_1h:by_project{cloud_project_name="IDAaaS"}
```

This returns instantly because the value is already computed.

## Setup

### 1. Copy the rules file

Copy `recording_rules.yml` to the Prometheus server, in the same directory as `prometheus.yml`.

### 2. Add to prometheus.yml

```yaml
rule_files:
  - "recording_rules.yml"
```

### 3. Reload Prometheus

```bash
# Option 1: Send SIGHUP
kill -HUP $(pidof prometheus)

# Option 2: HTTP reload (if --web.enable-lifecycle is enabled)
curl -X POST http://localhost:9090/-/reload

# Option 3: Restart the service
sudo systemctl restart prometheus
```

### 4. Verify

Open the Prometheus UI at `/rules` or query the API:

```bash
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups | length'
# Expected: 3
```

## Rule Groups

There are 3 groups with 16 rules total, each computing busy and idle CPU seconds at different granularities.

### Group 1: CPU Aggregations

**Name:** `ada_carbon_cpu_aggregations`
**Evaluation interval:** every 1 minute

Pre-aggregated CPU totals. These sum `node_cpu_seconds_total` across all CPU cores and modes.

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_total:by_project` | cloud_project_name | Busy CPU across all machines in a project |
| `ada:cpu_idle_seconds_total:by_project` | cloud_project_name | Idle CPU across all machines in a project |
| `ada:cpu_busy_seconds_total:by_project_machine` | cloud_project_name, machine_name | Busy CPU per machine type |
| `ada:cpu_idle_seconds_total:by_project_machine` | cloud_project_name, machine_name | Idle CPU per machine type |
| `ada:cpu_busy_seconds_total:by_project_machine_host` | cloud_project_name, machine_name, host | Busy CPU per individual host |
| `ada:cpu_idle_seconds_total:by_project_machine_host` | cloud_project_name, machine_name, host | Idle CPU per individual host |

**Busy** means all modes except `idle` (user, system, nice, irq, softirq, steal, iowait).
**Idle** means the `idle` mode only.

### Group 2: Hourly Increases

**Name:** `ada_carbon_hourly_increases`
**Evaluation interval:** every 5 minutes

These compute `increase(...[1h])` - the number of CPU seconds added in the last hour. The carbon API uses these directly for energy and carbon calculations.

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_increase_1h:by_project` | cloud_project_name | Hourly busy increase per project |
| `ada:cpu_idle_seconds_increase_1h:by_project` | cloud_project_name | Hourly idle increase per project |
| `ada:cpu_busy_seconds_increase_1h:by_project_machine` | cloud_project_name, machine_name | Hourly busy per machine type |
| `ada:cpu_idle_seconds_increase_1h:by_project_machine` | cloud_project_name, machine_name | Hourly idle per machine type |
| `ada:cpu_busy_seconds_increase_1h:by_project_machine_host` | cloud_project_name, machine_name, host | Hourly busy per host |
| `ada:cpu_idle_seconds_increase_1h:by_project_machine_host` | cloud_project_name, machine_name, host | Hourly idle per host |

### Group 3: Daily Increases

**Name:** `ada_carbon_daily_increases`
**Evaluation interval:** every 15 minutes

These compute `increase(...[1d])` for daily summary views and the heatmap.

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_increase_1d:by_project` | cloud_project_name | Daily busy increase per project |
| `ada:cpu_idle_seconds_increase_1d:by_project` | cloud_project_name | Daily idle increase per project |
| `ada:cpu_busy_seconds_increase_1d:by_project_machine` | cloud_project_name, machine_name | Daily busy per machine type |
| `ada:cpu_idle_seconds_increase_1d:by_project_machine` | cloud_project_name, machine_name | Daily idle per machine type |

## How the API Uses These Rules

The carbon monitoring API queries these recording rules to calculate energy and carbon:

```
1. Query: ada:cpu_busy_seconds_increase_1h:by_project{cloud_project_name="IDAaaS"}
   Result: 8313.1 busy CPU seconds in the last hour

2. Query: ada:cpu_idle_seconds_increase_1h:by_project{cloud_project_name="IDAaaS"}
   Result: 28564580 idle CPU seconds in the last hour

3. Calculate energy:
   busy_kwh = 12W x 8313.1s / 3,600,000 = 0.0277 kWh
   idle_kwh = 1W x 28564580s / 3,600,000 = 7.93 kWh
   total_kwh = 7.96 kWh

4. Get carbon intensity: 185 gCO2/kWh (from UK Grid API)

5. Calculate carbon: 7.96 kWh x 185 gCO2/kWh = 1472.6 gCO2eq
```

## Label Reference

The recording rules use these Prometheus labels from `node_cpu_seconds_total`:

| Label | Description | Examples |
|-------|-------------|----------|
| `cloud_project_name` | OpenStack project | IDAaaS, CDAaaS, DDAaaS |
| `machine_name` | Machine type within a project | Muon, Laser, Analysis, SANS |
| `host` | Individual machine hostname | 172.16.100.50, workspace-abc-muon-0 |
| `mode` | CPU mode | user, system, idle, iowait, nice, irq, softirq, steal |

## Naming Convention

Recording rule names follow the Prometheus convention:

```
ada:metric_name:aggregation_level
```

- `ada:` - namespace prefix
- `cpu_busy_seconds_total` or `cpu_busy_seconds_increase_1h` - what is being measured
- `by_project`, `by_project_machine`, `by_project_machine_host` - aggregation level
