# Estimated Electricity Usage and Carbon Footprint
```json
{
  "cloud_project_name": "project",
  "status": "processed",
  "date": "DD_MM_YYYY",
  "timeseries": {
    "00:00": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_second_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
      "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_second_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    }
  }
}
```

### Status
* fake: has usage data, but no cpu data
* not downloaded: no data in any field
* unprocessed: has cpu data, but no usage data  
* processed: All fields populated

## Machine Metrics
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

# Active Workspace Tracking

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