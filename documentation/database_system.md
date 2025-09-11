# Estimated Electricity Usage and Carbon Footprint
## By project (IDAaaS, CDAaaS, DDAaaS)
* Binned by hour
* Stored as a time series in parquet
* Seperate each projet into its own parquet file
## Parquet Schema
```parquet-schema
required INT64 timestamp (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS));
optional double busy_usage_cpu_seconds_total;
optional double idle_usage_cpu_seconds_total;
optional double busy_usage_kwh;
optional double idle_usage_kwh;
optional double busy_usage_gCO2eq;
optional double idle_usage_gCO2eq;
required binary status (STRING)
```

### Why (TIMESTAMP(isAdjustedToUTC=true, unit=MILLIS)) for timestamp?
### Parquet Efficiency 
Storing timestamps as integers is significantly more efficient in a columnar format like Parquet than using strings (like ISO 8601). Numeric types allow for:

* Better Compression: Integers compress very well.

* Faster Queries: Filtering and sorting on numbers is much faster than on strings.

* Predicate Pushdown: Data systems can efficiently skip entire blocks of data based on numeric timestamp ranges without needing to read them.

### Prometheus Compatibility

Prometheus uses a Unix timestamp for its time-series data model. When you query Prometheus or export data to it, using a millisecond-precision Unix timestamp is the native format. This means no conversion is necessary, making interactions seamless and fast.

### Carbon Intensity API Handling

The UK's Carbon Intensity API requires the ISO 8601 format (e.g., 2025-09-11T10:30Z). While this is a string, the conversion from a Unix timestamp is a trivial and computationally cheap operation that you would perform in your application code just before making the API call.

### Status
* not downloaded
* download incomplete
* unprocessed
* processed
* fake

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