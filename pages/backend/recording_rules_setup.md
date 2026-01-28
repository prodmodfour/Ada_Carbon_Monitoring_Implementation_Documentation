---
title: Recording Rules Setup
parent: Backend
nav_order: 4
---

# Setting Up Prometheus Recording Rules


Hi Jounaid,

Here are instructions for adding the carbon monitoring recording rules to the production Prometheus server (host-172-16-100-248.nubes.stfc.ac.uk).

These rules pre-aggregate common queries so the carbon dashboard loads quickly instead of running expensive increase() queries on every API call.


## What you need

1. The recording rules file from the ada-carbon-monitoring-api repository:
   `prometheus-preprod/prometheus/recording_rules.yml`

2. SSH access to the Prometheus server


## Steps

### 1. Copy the rules file to the Prometheus server

Copy `recording_rules.yml` to wherever your Prometheus config lives on the server. Typically this is the same directory as `prometheus.yml`.

```bash
scp recording_rules.yml <prometheus-host>:/path/to/prometheus/recording_rules.yml
```

### 2. Add the rules file to prometheus.yml

Edit `prometheus.yml` on the Prometheus server and add (or update) the `rule_files` section:

```yaml
rule_files:
  - "recording_rules.yml"
```

If there are already other rule files listed, just add this one to the list.

### 3. Reload Prometheus

Either send a SIGHUP to the Prometheus process:

```bash
kill -HUP $(pidof prometheus)
```

Or if the `--web.enable-lifecycle` flag is enabled, use the HTTP reload endpoint:

```bash
curl -X POST http://localhost:9090/-/reload
```

Or restart the Prometheus service:

```bash
sudo systemctl restart prometheus
```

### 4. Verify the rules loaded

Check that all 3 rule groups and 16 rules are present:

```bash
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool | head -20
```

Or open the Prometheus UI at https://host-172-16-100-248.nubes.stfc.ac.uk/rules and confirm you see:

- ada_carbon_cpu_aggregations (6 rules)
- ada_carbon_hourly_increases (6 rules)
- ada_carbon_daily_increases (4 rules)

### 5. Test a recording rule query

Run a quick test to make sure the rules are producing data:

```promql
ada:cpu_busy_seconds_total:by_project
```

This should return results with `cloud_project_name` labels like IDAaaS, CDAaaS, etc.


## What the rules do

The rules compute 3 things at different granularities (project, project+machine, project+machine+host):

1. **CPU totals** (evaluated every 1 minute) - Running totals of busy and idle CPU seconds
2. **Hourly increases** (evaluated every 5 minutes) - How many CPU seconds were added in the last hour, used directly for energy/carbon calculations
3. **Daily increases** (evaluated every 15 minutes) - How many CPU seconds were added in the last day, used for daily summary views

Without these rules, the carbon monitoring API has to run raw `increase(node_cpu_seconds_total{...}[1h])` queries which can be slow when there are many time series.


## File reference

The full rules file is in the repository at:
`ada-carbon-monitoring-api/prometheus-preprod/prometheus/recording_rules.yml`

Let me know if you run into any issues.

Ashraf
