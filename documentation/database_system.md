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