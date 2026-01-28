---
title: Backend
nav_order: 6
nav_exclude: false
has_children: true
---

# Backend Architecture

The carbon monitoring backend is implemented in `ada-carbon-monitoring-api`, a FastAPI service that calculates carbon footprint from CPU usage data.

## Overview

```
ada-carbon-monitoring-api/
├── main.py                 # FastAPI application entry point
├── src/
│   ├── api/carbon/         # API route handlers
│   │   ├── carbon_route.py     # Carbon calculation endpoints
│   │   ├── workspace_route.py  # Workspace/user/group endpoints
│   │   ├── history_route.py    # Historical data endpoints
│   │   └── carbon_schema.py    # Pydantic models
│   ├── calculators/        # Calculation logic
│   │   ├── electricity_estimator.py  # kWh from CPU seconds
│   │   ├── carbon_calculator.py      # gCO2eq from kWh
│   │   └── carbon_equivalency.py     # Real-world equivalencies
│   ├── clients/            # External service clients
│   │   ├── prometheus_client.py      # Prometheus queries
│   │   ├── mongodb_client.py         # MongoDB queries
│   │   ├── register_client.py        # ada-db-interface client
│   │   └── carbon_intensity_client.py # UK Grid API
│   ├── models/             # Domain models
│   │   ├── workspace_tracker.py      # Main tracking logic
│   │   └── workspace_usage.py        # Usage data model
│   └── config.py           # Configuration management
├── tests/                  # Test suite
└── ada-carbon-monitoring-api.ini  # Configuration file
```

## Configuration

The API is configured via `ada-carbon-monitoring-api.ini`:

```ini
[GENERAL]
version = 1.0.0
port = 8000
cors_allowed_origins = http://localhost:3000,https://ada.stfc.ac.uk

[PROMETHEUS]
url = https://host-172-16-100-248.nubes.stfc.ac.uk/
timeout = 120

[CARBON_INTENSITY]
api_url = https://api.carbonintensity.org.uk/intensity

[POWER]
busy_power_w = 12.0
idle_power_w = 1.0
cpu_tdp_w = 100.0

[TESTING]
use_fake_prometheus = false
use_fake_mongodb = false
use_fake_carbon_intensity = false
```

## API Routers

### Carbon Router (`/carbon`)

Core carbon calculation endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/carbon/intensity/current` | GET | Current UK grid carbon intensity |
| `/carbon/intensity/forecast` | GET | 24/48 hour intensity forecast |
| `/carbon/calculate` | POST | Calculate carbon from CPU seconds |
| `/carbon/equivalencies` | POST | Calculate equivalencies |
| `/carbon/equivalencies/{gco2eq}` | GET | Get equivalencies for value |
| `/carbon/electricity/estimate` | GET | Estimate electricity usage |

### Workspace Router (`/workspaces`)

Workspace carbon tracking:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workspaces/active` | GET | List active workspaces |
| `/workspaces/track` | POST | Track all active workspaces |
| `/workspaces/summary` | GET | Get summary statistics |
| `/workspaces/{id}` | GET | Get specific workspace usage |

### User Router (`/users`)

Per-user carbon attribution:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/{username}/usage` | GET | User's workspace carbon usage |
| `/users/{username}/summary` | GET | User's aggregated carbon summary |

### Group Router (`/groups`)

Per-group carbon attribution:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/groups` | GET | List all groups (cloud_project + machine_name) |
| `/groups/{name}/usage` | GET | Group's carbon usage |
| `/groups/{name}/summary` | GET | Group's aggregated carbon summary |

### History Router (`/carbon`)

Historical data for charts:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/carbon/history` | GET | Historical data (day/month/year view) |
| `/carbon/heatmap` | GET | Heatmap data (year of daily values) |

## Calculators

### ElectricityEstimator

Converts CPU seconds to energy (kWh):

```python
class ElectricityEstimator:
    def __init__(self, busy_power_w=12.0, idle_power_w=1.0):
        self.busy_power_w = busy_power_w
        self.idle_power_w = idle_power_w

    def estimate_total_kwh(self, busy_seconds, idle_seconds):
        watt_seconds = (self.busy_power_w * busy_seconds +
                       self.idle_power_w * idle_seconds)
        return watt_seconds / 3_600_000  # Convert to kWh
```

### CarbonCalculator

Converts energy to carbon emissions:

```python
class CarbonCalculator:
    def estimate_carbon_footprint(self, kwh, carbon_intensity_g_per_kwh):
        return kwh * carbon_intensity_g_per_kwh  # Returns gCO2eq
```

### CarbonEquivalencyCalculator

Converts gCO2eq to relatable equivalencies:

```python
EQUIVALENCIES = {
    "miles_driven_car": 400.0,      # gCO2eq per mile
    "smartphone_charge": 8.22,       # gCO2eq per charge
    "tree_day": 59.6,               # gCO2eq absorbed per tree per day
    "streaming_hour": 55.0,         # gCO2eq per hour of HD streaming
    "kettle_boil": 70.0,            # gCO2eq per liter boiled
    # ... 18+ total equivalencies
}
```

## Clients

### PrometheusAPIClient

Queries CPU metrics from Prometheus:

```python
client = PrometheusAPIClient(prometheus_url="https://...")

# Get CPU usage breakdown
cpu_data = client.get_cpu_usage_breakdown(
    timestamp=datetime.now(),
    cloud_project_name="IDAaaS",
    machine_name="Muon",
    host="172.16.100.50"
)
# Returns: {"busy": 1234.5, "idle": 56789.0}
```

Query used:
```promql
increase(node_cpu_seconds_total{
    cloud_project_name="IDAaaS",
    machine_name="Muon",
    instance=~"172.16.100.50.*"
}[1h])
```

### MongoDBClient

Queries workspace and user data:

```python
client = MongoDBClient(
    mongo_uri="mongodb://...",
    database_name="ada"
)

# Get active workspaces
workspaces = client.get_active_workspaces(timestamp=datetime.now())

# Get user by platform name
user = client.get_user_by_platform_name("aa123456")
```

### CarbonIntensityAPIClient

Queries UK Grid carbon intensity:

```python
client = CarbonIntensityAPIClient()

# Current intensity
current = client.get_current_intensity()
# Returns: {"intensity": 185, "index": "moderate"}

# Forecast
forecast = client.get_forecast(hours=24)
# Returns: {"forecasts": [...]}
```

## WorkspaceTracker

Main orchestration class that combines all components:

```python
class WorkspaceTracker:
    def __init__(self, ...):
        self.data_client = MongoDBClient(...)
        self.prometheus_client = PrometheusAPIClient(...)
        self.carbon_client = CarbonIntensityAPIClient()
        self.electricity_estimator = ElectricityEstimator(...)
        self.carbon_calculator = CarbonCalculator(...)

    def track_workspace(self, workspace, timestamp):
        # 1. Get CPU data from Prometheus
        cpu_data = self.prometheus_client.get_cpu_usage_breakdown(...)

        # 2. Calculate energy
        energy_kwh = self.electricity_estimator.estimate_total_kwh(...)

        # 3. Get carbon intensity
        intensity = self.carbon_client.get_current_intensity()

        # 4. Calculate carbon
        carbon_gco2eq = self.carbon_calculator.estimate_carbon_footprint(...)

        # 5. Get equivalencies
        equivalencies = self.equivalency_calc.get_top_equivalencies(...)

        return WorkspaceUsageEntry(...)

    def track_group(self, cloud_project_name, machine_name, timestamp):
        # Track aggregated usage for a group (no host filter)
        ...
```

## Data Models

### WorkspaceUsageEntry

```python
class WorkspaceUsageEntry:
    workspace_id: str
    hostname: str
    owner: Optional[str]
    timestamp: datetime

    # CPU metrics
    busy_cpu_seconds_total: float
    idle_cpu_seconds_total: float

    # Energy (kWh)
    busy_usage_kwh: float
    idle_usage_kwh: float
    total_usage_kwh: float

    # Carbon (gCO2eq)
    busy_usage_gco2eq: float
    idle_usage_gco2eq: float
    total_usage_gco2eq: float
    carbon_intensity_g_per_kwh: float

    # Equivalencies
    carbon_equivalencies: dict

    # Status
    status: str  # "initialized", "downloaded", "processed", "complete"
```

## Prometheus Recording Rules

Recording rules pre-aggregate common queries for faster dashboard loading. Without them, each API call runs expensive `increase()` queries across all time series.

The rules file is at `prometheus-preprod/prometheus/recording_rules.yml` in ada-carbon-monitoring-api.

### Adding to Prometheus

Add to your `prometheus.yml`:

```yaml
rule_files:
  - "recording_rules.yml"
```

### Rule Groups

**Group 1: `ada_carbon_cpu_aggregations`** (interval: 1m)

Pre-aggregated CPU totals at different granularities:

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_total:by_project` | cloud_project_name | Busy CPU across all machines in a project |
| `ada:cpu_idle_seconds_total:by_project` | cloud_project_name | Idle CPU across all machines in a project |
| `ada:cpu_busy_seconds_total:by_project_machine` | cloud_project_name, machine_name | Busy CPU per machine type |
| `ada:cpu_idle_seconds_total:by_project_machine` | cloud_project_name, machine_name | Idle CPU per machine type |
| `ada:cpu_busy_seconds_total:by_project_machine_host` | cloud_project_name, machine_name, host | Busy CPU per host |
| `ada:cpu_idle_seconds_total:by_project_machine_host` | cloud_project_name, machine_name, host | Idle CPU per host |

**Group 2: `ada_carbon_hourly_increases`** (interval: 5m)

Hourly CPU increases used directly for energy calculations:

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_increase_1h:by_project` | cloud_project_name | Hourly busy increase per project |
| `ada:cpu_idle_seconds_increase_1h:by_project` | cloud_project_name | Hourly idle increase per project |
| `ada:cpu_busy_seconds_increase_1h:by_project_machine` | cloud_project_name, machine_name | Hourly busy per machine |
| `ada:cpu_idle_seconds_increase_1h:by_project_machine` | cloud_project_name, machine_name | Hourly idle per machine |
| `ada:cpu_busy_seconds_increase_1h:by_project_machine_host` | cloud_project_name, machine_name, host | Hourly busy per host |
| `ada:cpu_idle_seconds_increase_1h:by_project_machine_host` | cloud_project_name, machine_name, host | Hourly idle per host |

**Group 3: `ada_carbon_daily_increases`** (interval: 15m)

Daily CPU increases for summary views:

| Rule | Labels | Description |
|------|--------|-------------|
| `ada:cpu_busy_seconds_increase_1d:by_project` | cloud_project_name | Daily busy increase per project |
| `ada:cpu_idle_seconds_increase_1d:by_project` | cloud_project_name | Daily idle increase per project |
| `ada:cpu_busy_seconds_increase_1d:by_project_machine` | cloud_project_name, machine_name | Daily busy per machine |
| `ada:cpu_idle_seconds_increase_1d:by_project_machine` | cloud_project_name, machine_name | Daily idle per machine |

### Example: Using Recording Rules

Instead of running the expensive raw query:

```promql
sum by (cloud_project_name) (
  increase(node_cpu_seconds_total{mode!="idle", cloud_project_name="IDAaaS"}[1h])
)
```

Query the pre-computed recording rule:

```promql
ada:cpu_busy_seconds_increase_1h:by_project{cloud_project_name="IDAaaS"}
```

### Verifying Rules Are Loaded

```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups | length'
# Expected: 3

curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules | length'
# Expected: 6, 6, 4 (16 total rules)
```

---

## Running the API

```bash
# Development
python main.py

# Production with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMETHEUS_URL` | Prometheus server URL | localhost:9090 |
| `MONGO_URI` | MongoDB connection URI | localhost:27017 |
| `MONGO_DATABASE` | MongoDB database name | ada |
| `USE_FAKE_PROMETHEUS` | Use fake Prometheus data | false |
| `USE_FAKE_MONGODB` | Use fake MongoDB data | false |
