---
title: Database System     
nav_order: 2         
nav_exclude: false     
---

# Data acquisition breakdown
We store:
* idle_cpu_seconds
* busy_cpu_seconds
* idle_kwh
* busy_kwh
* idle_gCo2eq
* busy_gCo2eq

We store data in a timeseries format for the last year. Data is stored in JSON files.

We store this data for each:
* Project
* Experiment
* Machine
* User

First, we download cpu_seconds data day by day. We make a request for an hours worth of cpu_seconds data.
This gives us a JSON object with a number of timeseries. We parse this object and save its data to various storage classes.
We have a usage storage class for each level of storage mentioned before. If the download fails, we store "failed" instead of a float.



We seperate data into hourly, monthly and yearly so that we can easily load this data to our graphs.

# EstimatedUsageDayEntry
```json
{
  "cloud_project_name": "project",
  "date": "DD_MM_YYYY",
  "timeseries": {
    "totals": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
      "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    },
    "00:00": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
        "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    }
  }
}
```

## MachineMetrics
```json
{
  "machine_name": "Artemis Matlab",
  "metrics": {
    "energy_kwh": {
      "busy": {
        "average": 0.0
      },
      "idle": {
        "average": 0.0
      }
    },
    "carbon_gCo2eq": {
        "busy": {
            "average": 0.0
        },
        "idle": {
            "average": 0.0
      }
    }
  }
}
```

# ActiveWorkspace

* Stored in JSON
```json
{
    "instance": "instance="host-172-16-100-116.nubes.stfc.ac.uk:9100"",
    "machine_name": "Artemis (Matlab)",
    "busy_kwh": 0,
    "idle_kwh": 0,
    "busy_gCo2eq": 0,
    "idle_gCo2eq": 0
    "started_at": "2025-09-11T10:30:00Z"
}
```