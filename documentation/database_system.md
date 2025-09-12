# Estimated Electricity Usage and Carbon Footprint
## By project (IDAaaS, CDAaaS, DDAaaS)
* Binned by hour
* Stored as a time series in parquet
* Each hour is stored as a json file
* Each json file contains the following fields:
  * timestamp
  * busy_cpu_seconds_total
  * idle_cpu_seconds_total
  * busy_usage_kwh
  * idle_usage_kwh
  * busy_usage_gCO2eq
  * idle_usage_gCO2eq
  * status


### Status
* fake: has usage data, but no cpu data
* not downloaded: no data in any field
* unprocessed: has cpu data, but no usage data  
* processed: All fields populated

## Average Electricity Usage and Carbon Footprint
### By Machine name
* Running average
* Stored in JSON

```json
{
  "machine_name": "Artemis Matlab",
  "metrics": {
    "energy_kwh": {
      "busy": {
        "number_data_points": 0,
        "running_average": 0
      },
      "idle": {
        "number_data_points": 0,
        "running_average": 0
      }
    },
    "carbon_gCo2eq": {
        "number_data_points": 0,
        "busy": {
            "running_average": 0
        },
        "idle": {
            "running_average": 0
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