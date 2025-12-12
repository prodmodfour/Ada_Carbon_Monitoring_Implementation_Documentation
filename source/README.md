# Ada Carbon Monitoring Implementation

## Overview

Complete implementation of carbon monitoring and tracking system for Ada platform. This implementation integrates MongoDB, Prometheus, and Carbon Intensity APIs to provide comprehensive carbon footprint tracking and reporting.

## Project Structure

```
source/
├── mongodb/                    # MongoDB integration
│   ├── MongoDBClient.py       # MongoDB client for user/group attribution
│   ├── __init__.py
│   └── README.md
│
├── prometheus/                 # Prometheus integration
│   ├── PrometheusAPIClient.py # Prometheus metrics client
│   └── prometheus_queries.py
│
├── usage_calculation/          # Usage and carbon calculations
│   ├── CarbonIntensityAPIClient.py  # UK Carbon Intensity API client
│   ├── ElectricityEstimator.py      # Electricity usage estimation (busy/idle)
│   ├── CarbonCalculator.py          # Carbon footprint calculator
│   └── usage_calculation_functions.py  # Legacy functions
│
├── workspace_tracking/         # Workspace usage tracking
│   ├── WorkspaceTracker.py    # Main workspace tracker orchestration
│   ├── WorkspaceUsageEntry.py # Data model for workspace usage
│   ├── CarbonEquivalencyCalculator.py  # Carbon equivalency translations
│   ├── __init__.py
│   └── README.md
│
├── storage/                    # Data storage models
│   ├── EstimatedUsageEntry.py
│   ├── EstimatedUsageHourEntry.py
│   ├── Machine.py
│   └── JSON_functions.py
│
├── charts/                     # Visualization components
│   └── (Svelte components - see notes/)
│
└── tests/                      # Unit tests
    ├── test_electricity_estimator.py
    ├── test_carbon_calculator.py
    ├── test_carbon_equivalency.py
    ├── __init__.py
    └── README.md
```

## Core Components

### 1. Data Aggregation

#### MongoDBClient
- Queries Ada MongoDB for users, groups, and workspaces
- Attributes resource usage to specific users and groups
- Time-based workspace ownership tracking
- Group naming convention: `{cloud_project_name}_{machine_name}`

**Location**: `mongodb/MongoDBClient.py`

#### PrometheusAPIClient
- Retrieves CPU usage metrics (`node_cpu_seconds_total`)
- Supports filtering by cloud project, machine, and host
- RFC3339 timestamp formatting
- Configurable timeout and error handling

**Location**: `prometheus/PrometheusAPIClient.py`

#### CarbonIntensityAPIClient
- Fetches real-time UK grid carbon intensity
- Averages two 30-minute periods for hourly data
- Returns gCO2 per kWh

**Location**: `usage_calculation/CarbonIntensityAPIClient.py`

### 2. Calculation Engines

#### ElectricityEstimator
Estimates electricity usage from CPU busy/idle times:
- Separate power constants for busy (12W) and idle (1W) states
- More accurate than simple TDP-based methods
- Provides detailed breakdown of usage

**Location**: `usage_calculation/ElectricityEstimator.py`

**Example**:
```python
from usage_calculation.ElectricityEstimator import ElectricityEstimator

estimator = ElectricityEstimator(busy_power_w=12, idle_power_w=1)
kwh = estimator.estimate_usage_kwh(
    busy_cpu_seconds=18000,  # 5 hours
    idle_cpu_seconds=54000   # 15 hours
)
# Returns: 0.075 kWh
```

#### CarbonCalculator
Calculates carbon footprint by integrating electricity and carbon intensity:
- TDP-based calculation method
- Detailed busy/idle calculation method
- Direct kWh to carbon conversion
- Automatic carbon intensity fetching

**Location**: `usage_calculation/CarbonCalculator.py`

**Example**:
```python
from usage_calculation.CarbonCalculator import CarbonCalculator
from datetime import datetime

calculator = CarbonCalculator()

# Detailed calculation
result = calculator.estimate_carbon_footprint_detailed(
    busy_cpu_seconds=18000,
    idle_cpu_seconds=54000,
    busy_power_w=12,
    idle_power_w=1,
    start_time=datetime.now()
)
# Returns: {electricity_kwh: {...}, carbon_gco2eq: {...}, ...}
```

#### CarbonEquivalencyCalculator
Translates carbon emissions into relatable real-world comparisons:
- Miles driven in average car
- Smartphone/laptop charges
- Hours of LED bulb usage or video streaming
- Liters of water boiled in kettle
- Trees needed for carbon offset
- And 10+ more equivalencies

**Location**: `workspace_tracking/CarbonEquivalencyCalculator.py`

**Example**:
```python
from workspace_tracking.CarbonEquivalencyCalculator import CarbonEquivalencyCalculator

calc = CarbonEquivalencyCalculator()
equivalencies = calc.get_top_equivalencies(1000, count=5)  # 1000 gCO2eq
# Returns top 5 most relatable equivalencies
```

### 3. Workspace Tracking

#### WorkspaceTracker
Main orchestration class that:
- Finds all active workspaces from MongoDB
- Queries Prometheus for CPU usage
- Calculates electricity and carbon metrics
- Generates carbon equivalencies
- Provides summary statistics
- Exports data to JSON

**Location**: `workspace_tracking/WorkspaceTracker.py`

**Example**:
```python
from workspace_tracking import WorkspaceTracker
from datetime import datetime

tracker = WorkspaceTracker(
    mongo_uri="mongodb://localhost:27017/",
    mongo_db="ada",
    prometheus_url="https://prometheus.example.com/"
)

# Track all active workspaces
tracked = tracker.track_all_active_workspaces(
    timestamp=datetime.now(),
    cloud_project_name="CDAaaS",
    machine_name="MUON"
)

# Get summary
summary = tracker.get_summary_statistics()
print(f"Total Energy: {summary['total_energy_kwh']:.2f} kWh")
print(f"Total Carbon: {summary['total_carbon_gco2eq']:.2f} gCO2eq")

# Export
tracker.export_to_json("workspace_usage.json")
tracker.close()
```

#### WorkspaceUsageEntry
Data model for individual workspace metrics:
- Workspace identification and ownership
- CPU usage (busy/idle)
- Energy consumption (kWh)
- Carbon emissions (gCO2eq)
- Carbon equivalencies
- Status tracking (initialized → downloaded → processed → complete)

**Location**: `workspace_tracking/WorkspaceUsageEntry.py`

## Data Flow

### Complete Workflow

```
1. MongoDB Query
   ↓
   Active Workspaces + User Attribution
   ↓
2. Prometheus Query
   ↓
   CPU Metrics (busy/idle seconds)
   ↓
3. ElectricityEstimator
   ↓
   Energy Usage (kWh)
   ↓
4. Carbon Intensity API
   ↓
   Grid Carbon Intensity (gCO2/kWh)
   ↓
5. CarbonCalculator
   ↓
   Carbon Emissions (gCO2eq)
   ↓
6. CarbonEquivalencyCalculator
   ↓
   Relatable Comparisons
   ↓
7. WorkspaceUsageEntry
   ↓
   Complete Data Model
```

## Installation

### Python Dependencies

```bash
pip install pymongo[srv]==4.6.3
pip install requests
pip install pytest  # For running tests
pip install pytest-cov  # For coverage reports
```

### Configuration

1. **MongoDB Connection**:
```python
mongo_uri = "mongodb://username:password@localhost:27017/"
mongo_db = "ada"
```

2. **Prometheus URL**:
```python
prometheus_url = "https://prometheus.example.com/"
```

3. **Carbon Intensity API**:
No configuration needed - uses UK public API

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=usage_calculation --cov=workspace_tracking

# Run specific test
python -m pytest tests/test_electricity_estimator.py -v
```

## Usage Examples

### Example 1: Track Single Workspace

```python
from workspace_tracking import WorkspaceTracker
from datetime import datetime

tracker = WorkspaceTracker(
    mongo_uri="mongodb://localhost:27017/",
    mongo_db="ada"
)

# Get active workspaces
workspaces = tracker.get_active_workspaces()

# Track first workspace
if workspaces:
    entry = tracker.track_workspace(
        workspace=workspaces[0],
        timestamp=datetime.now(),
        cloud_project_name="CDAaaS",
        machine_name="MUON"
    )

    print(f"Workspace: {entry.hostname}")
    print(f"Owner: {entry.owner}")
    print(f"Energy: {entry.total_usage_kwh:.4f} kWh")
    print(f"Carbon: {entry.total_usage_gco2eq:.2f} gCO2eq")

    if entry.carbon_equivalencies:
        for key, equiv in entry.carbon_equivalencies['top_equivalencies'].items():
            print(f"  - {equiv['value']:.2f} {equiv['description']}")

tracker.close()
```

### Example 2: Calculate Carbon for CPU Usage

```python
from usage_calculation.CarbonCalculator import CarbonCalculator
from datetime import datetime

calculator = CarbonCalculator()

# Using detailed busy/idle method
result = calculator.estimate_carbon_footprint_detailed(
    busy_cpu_seconds=3600,   # 1 hour busy
    idle_cpu_seconds=10800,  # 3 hours idle
    busy_power_w=12,
    idle_power_w=1,
    start_time=datetime.now()
)

print(f"Busy Energy: {result['electricity_kwh']['busy']:.4f} kWh")
print(f"Idle Energy: {result['electricity_kwh']['idle']:.4f} kWh")
print(f"Total Energy: {result['electricity_kwh']['total']:.4f} kWh")
print(f"Carbon Intensity: {result['carbon_intensity_g_per_kwh']:.2f} g/kWh")
print(f"Total Carbon: {result['carbon_gco2eq']['total']:.2f} gCO2eq")
```

### Example 3: MongoDB User Attribution

```python
from mongodb.MongoDBClient import MongoDBClient
from datetime import datetime

client = MongoDBClient(
    mongo_uri="mongodb://localhost:27017/",
    database_name="ada"
)

# Find user at specific time
user = client.get_user_by_host_and_time(
    hostname="172.16.100.50",
    timestamp=datetime(2025, 9, 23, 17, 0, 0)
)

if user:
    print(f"User: {user['platform_name']}")
    print(f"Name: {user['name']}")
    print(f"Email: {user['email']}")

# Find group by project and machine
group = client.get_group_by_cloud_project_and_machine(
    cloud_project_name="CDAaaS",
    machine_name="MUON"
)

if group:
    print(f"Group: {group['name']}")
    print(f"Members: {group['members']}")

client.close()
```

## API Integration

For integration with Ada API, see `notes/changes_to_add/carbon_monitoring_api.md`

Components to expose:
- CarbonCalculator
- CarbonEquivalencyCalculator
- WorkspaceTracker
- Data aggregators (MongoDB, Prometheus clients)
- ElectricityEstimator

## Frontend Widgets

Svelte 3 components for visualization (see `notes/changes_to_add/carbon_monitoring_widgets.md`):

1. **Stacked Bar Chart**: Electricity/Carbon usage by day/week/month/year
2. **GitHub-style Heatmap**: Daily carbon usage calendar view
3. **Workspace Card**: Live workspace usage display with equivalencies

## Performance Considerations

- **MongoDB**: Connection pooling handled automatically
- **Prometheus**: Configurable timeouts (default 120s)
- **Carbon Intensity API**: 15-minute self-cleaning cache
- **Batch Processing**: Track multiple workspaces in single call
- **Memory**: Efficient data structures, no unnecessary caching

## Best Practices

1. **Always close connections**:
   ```python
   tracker.close()
   client.close()
   ```

2. **Handle None returns**:
   ```python
   result = client.get_user_by_host_and_time(...)
   if result:
       # Use result
   ```

3. **Use timezone-aware timestamps**:
   ```python
   from datetime import datetime, timezone
   timestamp = datetime.now(timezone.utc)
   ```

4. **Batch operations when possible**:
   ```python
   # Good: Track all at once
   tracker.track_all_active_workspaces()

   # Avoid: Track one by one in loop
   ```

## License

See main project LICENSE file.

## Contributing

See CONTRIBUTING.md for development guidelines.
