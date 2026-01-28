---
title: API Reference
nav_order: 3
nav_exclude: false
---

# API Reference

Complete documentation for the Ada Carbon Monitoring API.

**Base URL:** `http://localhost:8000` (or your deployment URL)

## Carbon Endpoints

### Get Current Intensity

Get the current UK grid carbon intensity.

```
GET /carbon/intensity/current
```

**Response:**
```json
{
  "timestamp": "2026-01-28T12:00:00Z",
  "intensity": 185,
  "index": "moderate",
  "from": "2026-01-28T11:30:00Z",
  "to": "2026-01-28T12:00:00Z"
}
```

**Intensity Index Values:**
- `very low` - < 50 gCO2/kWh
- `low` - 50-100 gCO2/kWh
- `moderate` - 100-200 gCO2/kWh
- `high` - 200-300 gCO2/kWh
- `very high` - > 300 gCO2/kWh

---

### Get Intensity Forecast

Get carbon intensity forecast for the next 24-48 hours.

```
GET /carbon/intensity/forecast?hours=24
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| hours | int | No | Forecast hours (1-48, default: 24) |

**Response:**
```json
{
  "forecasts": [
    {
      "from_time": "2026-01-28T12:00Z",
      "to_time": "2026-01-28T12:30Z",
      "intensity_forecast": 185,
      "intensity_index": "moderate"
    },
    ...
  ]
}
```

---

### Calculate Carbon Footprint

Calculate carbon footprint from CPU usage.

```
POST /carbon/calculate
```

**Request Body:**
```json
{
  "busy_cpu_seconds": 1000,
  "idle_cpu_seconds": 5000,
  "busy_power_w": 12.0,      // optional, default: 12
  "idle_power_w": 1.0,       // optional, default: 1
  "carbon_intensity_g_per_kwh": 185  // optional, fetches current if not provided
}
```

**Response:**
```json
{
  "electricity_kwh": {
    "busy": 0.00333,
    "idle": 0.00139,
    "total": 0.00472
  },
  "carbon_gco2eq": {
    "busy": 0.617,
    "idle": 0.257,
    "total": 0.874
  },
  "carbon_intensity_g_per_kwh": 185,
  "power_w": {
    "busy": 12.0,
    "idle": 1.0
  },
  "equivalencies": {
    "total_gco2eq": 0.874,
    "top_equivalencies": {
      "smartphone_charges": {"value": 0.11, "unit": "charges", "description": "..."},
      ...
    }
  }
}
```

---

### Get Equivalencies

Get carbon equivalencies for a given amount of CO2.

```
GET /carbon/equivalencies/{gco2eq}?count=5
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| gco2eq | float | Yes | Carbon amount in gCO2eq |
| count | int | No | Number of equivalencies (1-15, default: 5) |

**Response:**
```json
{
  "total_gco2eq": 1000,
  "top_equivalencies": {
    "miles_driven": {
      "value": 2.5,
      "unit": "miles",
      "description": "Miles driven in an average passenger vehicle"
    },
    "smartphone_charges": {
      "value": 121.7,
      "unit": "charges",
      "description": "Smartphone battery charges (full cycle)"
    },
    "trees_day": {
      "value": 16.8,
      "unit": "tree-days",
      "description": "Trees needed for one day to offset emissions"
    },
    "streaming_hours": {
      "value": 18.2,
      "unit": "hours",
      "description": "Hours of HD video streaming"
    },
    "kettles_boiled": {
      "value": 14.3,
      "unit": "liters",
      "description": "Liters of water boiled in an electric kettle"
    }
  }
}
```

---

### Estimate Electricity

Estimate electricity usage from CPU seconds.

```
GET /carbon/electricity/estimate?busy_cpu_seconds=1000&idle_cpu_seconds=5000
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| busy_cpu_seconds | float | Yes | Busy CPU seconds |
| idle_cpu_seconds | float | Yes | Idle CPU seconds |
| busy_power_w | float | No | Busy power in watts (default: 12) |
| idle_power_w | float | No | Idle power in watts (default: 1) |

**Response:**
```json
{
  "busy_kwh": 0.00333,
  "idle_kwh": 0.00139,
  "total_kwh": 0.00472,
  "busy_power_w": 12.0,
  "idle_power_w": 1.0
}
```

---

## Workspace Endpoints

### Get Active Workspaces

List all currently active workspaces.

```
GET /workspaces/active
```

**Response:**
```json
[
  {
    "_id": "...",
    "hostname": "172.16.100.50",
    "owner": "aa123456",
    "tag": "ISIS",
    "state": "READY",
    "created_time": "2026-01-28T09:00:00Z"
  },
  ...
]
```

---

### Track Workspaces

Track carbon usage for all active workspaces.

```
POST /workspaces/track
```

**Request Body:**
```json
{
  "cloud_project_name": "IDAaaS",
  "machine_name": "Muon",      // optional
  "timestamp": "2026-01-28T12:00:00Z"  // optional, default: now
}
```

**Response:**
```json
{
  "tracked_count": 8,
  "timestamp": "2026-01-28T12:00:00Z",
  "workspaces": [
    {
      "workspace_id": "...",
      "hostname": "172.16.100.50",
      "owner": "aa123456",
      "user_info": {
        "platform_name": "aa123456",
        "name": "Andrew Smith",
        "email": "andrew.smith@stfc.ac.uk"
      },
      "cpu_usage": {
        "busy_seconds": 1234.5,
        "idle_seconds": 56789.0,
        "total_seconds": 58023.5
      },
      "energy_kwh": {
        "busy": 0.00411,
        "idle": 0.01578,
        "total": 0.01989
      },
      "carbon_gco2eq": {
        "busy": 0.76,
        "idle": 2.92,
        "total": 3.68
      },
      "carbon_intensity_g_per_kwh": 185,
      "status": "complete"
    },
    ...
  ]
}
```

---

### Get Workspace Summary

Get aggregated summary for tracked workspaces.

```
GET /workspaces/summary?cloud_project_name=IDAaaS
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| cloud_project_name | string | Yes | Cloud project name |
| machine_name | string | No | Machine name filter |

**Response:**
```json
{
  "workspace_count": 8,
  "complete_count": 8,
  "total_cpu_seconds": {
    "busy_seconds": 12345.6,
    "idle_seconds": 567890.1,
    "total_seconds": 580235.7
  },
  "total_energy_kwh": 0.199,
  "total_carbon_gco2eq": 36.8,
  "carbon_equivalencies": {
    "total_gco2eq": 36.8,
    "top_equivalencies": {...}
  }
}
```

---

## User Endpoints

### Get User Carbon Usage

Get carbon usage for all workspaces owned by a user.

```
GET /users/{username}/usage
```

**Response:**
```json
[
  {
    "workspace_id": "...",
    "hostname": "172.16.100.50",
    "owner": "aa123456",
    "cpu_usage": {...},
    "energy_kwh": {...},
    "carbon_gco2eq": {...},
    "status": "complete"
  },
  ...
]
```

---

### Get User Carbon Summary

Get aggregated carbon summary for a user.

```
GET /users/{username}/summary
```

**Response:**
```json
{
  "workspace_count": 3,
  "complete_count": 3,
  "total_cpu_seconds": {
    "busy_seconds": 4500.0,
    "idle_seconds": 180000.0,
    "total_seconds": 184500.0
  },
  "total_energy_kwh": 0.065,
  "total_carbon_gco2eq": 12.0,
  "carbon_equivalencies": {...}
}
```

---

## Group Endpoints

### List Groups

List all available groups (cloud_project + machine_name combinations).

```
GET /groups
```

**Response:**
```json
{
  "groups": [
    {
      "name": "IDAaaS_Muon",
      "cloud_project": "IDAaaS",
      "machine_name": "Muon"
    },
    {
      "name": "IDAaaS_SANS",
      "cloud_project": "IDAaaS",
      "machine_name": "SANS"
    },
    {
      "name": "CDAaaS_Tomography",
      "cloud_project": "CDAaaS",
      "machine_name": "Tomography"
    }
  ],
  "count": 780
}
```

---

### Get Group Carbon Usage

Get carbon usage for a group.

```
GET /groups/{group_name}/usage
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_name | string | Yes | Format: `{cloud_project}_{machine_name}` |

**Example:** `GET /groups/IDAaaS_Muon/usage`

**Response:**
```json
[
  {
    "workspace_id": "IDAaaS_Muon",
    "hostname": "IDAaaS_Muon",
    "cpu_usage": {
      "busy_seconds": 537.45,
      "idle_seconds": 287239.26,
      "total_seconds": 287776.71
    },
    "energy_kwh": {
      "busy": 0.00179,
      "idle": 0.07979,
      "total": 0.08158
    },
    "carbon_gco2eq": {
      "busy": 0.41,
      "idle": 18.47,
      "total": 18.89
    },
    "status": "processed"
  }
]
```

---

### Get Group Carbon Summary

Get aggregated carbon summary for a group.

```
GET /groups/{group_name}/summary
```

**Response:**
```json
{
  "workspace_count": 1,
  "complete_count": 1,
  "total_cpu_seconds": {
    "busy_seconds": 537.45,
    "idle_seconds": 287239.26,
    "total_seconds": 287776.71
  },
  "total_energy_kwh": 0.08158,
  "total_carbon_gco2eq": 18.89,
  "carbon_equivalencies": {
    "total_gco2eq": 18.89,
    "top_equivalencies": {...}
  }
}
```

---

## History Endpoints

### Get Historical Data

Get historical carbon/electricity data for charts.

```
GET /carbon/history?view=day&data_type=carbon&cloud_project_name=IDAaaS
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| view | string | Yes | `day`, `month`, or `year` |
| data_type | string | Yes | `carbon` or `electricity` |
| cloud_project_name | string | No | Filter by project |
| machine_name | string | No | Filter by machine |
| date | string | No | For day view: `YYYY-MM-DD` |
| month | string | No | For month view: `YYYY-MM` |
| year | int | No | For year view |

**Response:**
```json
{
  "view": "day",
  "data_type": "carbon",
  "labels": ["00:00", "01:00", "02:00", ...],
  "busy": [12.5, 15.3, 8.7, ...],
  "idle": [3.2, 4.1, 2.8, ...]
}
```

---

### Get Heatmap Data

Get year heatmap data (GitHub-style).

```
GET /carbon/heatmap?year=2026&cloud_project_name=IDAaaS
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| year | int | Yes | Year to get data for |
| cloud_project_name | string | No | Filter by project |
| machine_name | string | No | Filter by machine |

**Response:**
```json
{
  "year": 2026,
  "days": [
    {"date": "2026-01-01", "value": 125.5},
    {"date": "2026-01-02", "value": 143.2},
    ...
  ],
  "max": 250.0
}
```

{: .note }
> Data before March 2025 returns 0 due to Prometheus label changes.

---

## Health & Config

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "api": "healthy",
    "prometheus": "healthy",
    "mongodb": "healthy",
    "carbon_intensity_api": "healthy"
  }
}
```

---

### Get Config

Get current configuration (non-sensitive).

```
GET /config
```

**Response:**
```json
{
  "version": "1.0.0",
  "prometheus_url": "https://...",
  "mongo_database": "ada",
  "power_config": {
    "busy_power_w": 12.0,
    "idle_power_w": 1.0,
    "cpu_tdp_w": 100.0
  },
  "supported_tags": ["ISIS", "CLF", "TRAINING", "DEV"],
  "testing": {
    "use_fake_prometheus": false,
    "use_fake_mongodb": false,
    "use_fake_carbon_intensity": false
  }
}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 500 | Internal server error |
