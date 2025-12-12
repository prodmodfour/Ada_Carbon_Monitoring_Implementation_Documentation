# Workspace Tracker

## Overview

The Workspace Tracker module integrates MongoDB, Prometheus, and Carbon Intensity APIs to provide comprehensive tracking of workspace resource usage and environmental impact.

## Features

- **Active Workspace Detection**: Automatically finds all active workspaces from MongoDB
- **User Attribution**: Links workspaces to specific users
- **Prometheus Integration**: Retrieves CPU usage metrics for workspace uptime
- **Energy Calculation**: Converts CPU usage to energy consumption (kWh)
- **Carbon Footprint**: Calculates carbon emissions (gCO2eq) using real-time carbon intensity
- **Carbon Equivalencies**: Translates emissions into relatable real-world comparisons
- **Data Persistence**: Store and export usage data in JSON format
- **Summary Statistics**: Aggregate metrics across all tracked workspaces

## Architecture

### Components

1. **WorkspaceTracker**: Main orchestration class
   - Coordinates all API clients
   - Manages workspace tracking lifecycle
   - Provides aggregation and export functionality

2. **WorkspaceUsageEntry**: Data model for workspace metrics
   - Stores CPU, energy, and carbon metrics
   - Tracks busy and idle states separately
   - Includes user attribution and carbon equivalencies

3. **CarbonEquivalencyCalculator**: Converts emissions to equivalencies
   - Miles driven in a car
   - Smartphone charges
   - Trees needed for offset
   - LED bulb hours
   - And more...

### Data Flow

```
MongoDB (Active Workspaces)
    ↓
WorkspaceTracker
    ↓
Prometheus (CPU Usage) → Energy Calculation (kWh)
    ↓
Carbon Intensity API → Carbon Calculation (gCO2eq)
    ↓
Carbon Equivalency Calculator → Relatable Comparisons
    ↓
WorkspaceUsageEntry (Complete Data Model)
```

## Installation

Ensure all dependencies are installed:

```bash
pip install pymongo[srv]==4.6.3
pip install requests
```

## Usage

### Basic Tracking

```python
from workspace_tracking import WorkspaceTracker
from datetime import datetime

# Initialize tracker
tracker = WorkspaceTracker(
    mongo_uri="mongodb://localhost:27017/",
    mongo_db="ada",
    prometheus_url="https://prometheus.example.com/",
    default_cpu_tdp_w=100.0  # CPU TDP in watts
)

# Track all active workspaces
timestamp = datetime.now()
tracked = tracker.track_all_active_workspaces(
    timestamp=timestamp,
    cloud_project_name="CDAaaS",
    machine_name="MUON"
)

print(f"Tracked {len(tracked)} workspaces")

# Clean up
tracker.close()
```

### Get Summary Statistics

```python
summary = tracker.get_summary_statistics()

print(f"Total Workspaces: {summary['workspace_count']}")
print(f"Total Energy: {summary['total_energy_kwh']:.2f} kWh")
print(f"Total Carbon: {summary['total_carbon_gco2eq']:.2f} gCO2eq")

# Display carbon equivalencies
if summary['carbon_equivalencies']:
    for key, equiv in summary['carbon_equivalencies']['top_equivalencies'].items():
        value = equiv['value']
        description = equiv['description']
        print(f"  - {value:.2f} {description}")
```

### Track Individual Workspace

```python
# Get active workspaces
workspaces = tracker.get_active_workspaces()

# Track specific workspace
if workspaces:
    entry = tracker.track_workspace(
        workspace=workspaces[0],
        timestamp=datetime.now(),
        cloud_project_name="CDAaaS",
        machine_name="MUON"
    )

    if entry:
        print(f"Status: {entry.status}")
        print(f"Energy: {entry.total_usage_kwh:.2f} kWh")
        print(f"Carbon: {entry.total_usage_gco2eq:.2f} gCO2eq")
```

### Export Data

```python
# Export all tracked workspaces to JSON
tracker.export_to_json(
    filepath="/path/to/output.json",
    pretty=True
)
```

### Access Individual Entries

```python
# Get all entries
entries = tracker.get_all_entries()

for entry in entries:
    print(f"\nWorkspace: {entry.workspace_id}")
    print(f"  Hostname: {entry.hostname}")
    print(f"  Owner: {entry.owner}")
    print(f"  Status: {entry.status}")

    if entry.user_info:
        print(f"  User: {entry.user_info['name']}")

    if entry.total_usage_gco2eq:
        print(f"  Carbon: {entry.total_usage_gco2eq:.2f} gCO2eq")

        if entry.carbon_equivalencies:
            print(f"  Equivalencies:")
            for key, equiv in entry.carbon_equivalencies['top_equivalencies'].items():
                print(f"    - {equiv['value']:.2f} {equiv['description']}")
```

## WorkspaceUsageEntry Data Model

Each workspace entry contains:

```python
{
    "workspace_id": "MongoDB workspace ID",
    "hostname": "172.16.100.50",
    "owner": "john.doe",
    "timestamp": "2025-09-23T17:00:00",
    "user_info": {
        "platform_name": "john.doe",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "uid": 1001
    },
    "cpu_usage": {
        "busy_seconds": 3600.0,
        "idle_seconds": 1800.0,
        "total_seconds": 5400.0
    },
    "energy_kwh": {
        "busy": 2.5,
        "idle": 1.0,
        "total": 3.5
    },
    "carbon_gco2eq": {
        "busy": 112.5,
        "idle": 45.0,
        "total": 157.5
    },
    "carbon_intensity_g_per_kwh": 45.0,
    "carbon_equivalencies": {
        "total_gco2eq": 157.5,
        "top_equivalencies": {
            "smartphone_charges": {
                "value": 19.15,
                "unit": "charges",
                "description": "Smartphone battery charges"
            }
        }
    },
    "cpu_tdp_w": 100.0,
    "status": "complete"
}
```

## Carbon Equivalencies

The calculator provides relatable comparisons including:

- **Transportation**: Miles/kilometers driven
- **Electronics**: Smartphone/laptop charges
- **Environmental**: Trees needed for carbon offset
- **Energy**: LED bulb hours
- **Fuel**: Gasoline/coal consumption
- **Products**: Plastic bottles, aluminum cans

Example:

```python
from workspace_tracking import CarbonEquivalencyCalculator

calc = CarbonEquivalencyCalculator()

# Get all equivalencies
equivalencies = calc.calculate_equivalencies(1000)  # 1000 gCO2eq

# Get top 5 most relatable
top = calc.get_top_equivalencies(1000, count=5)

# Format for display
print(calc.format_all_equivalencies(1000))
```

## Status Values

Workspace entries progress through these statuses:

- `initialized`: Entry created
- `downloaded`: CPU data retrieved from Prometheus
- `processed`: Energy and carbon calculated
- `complete`: All data including user info and equivalencies

## Configuration

### MongoDB Settings

```python
tracker = WorkspaceTracker(
    mongo_uri="mongodb://user:pass@localhost:27017/",
    mongo_db="ada",
    mongo_user="username",    # Optional
    mongo_pass="password"     # Optional
)
```

### Prometheus Settings

```python
tracker = WorkspaceTracker(
    prometheus_url="https://prometheus.example.com/"
)
```

### CPU TDP

Default CPU TDP (Thermal Design Power) in watts:

```python
tracker = WorkspaceTracker(
    default_cpu_tdp_w=150.0  # For high-performance workstations
)
```

## Error Handling

The tracker handles errors gracefully:

- Missing Prometheus data: Returns None, continues with other workspaces
- MongoDB connection issues: Raises exception on initialization
- Invalid workspace data: Skips workspace, logs warning
- API failures: Retries with exponential backoff (Prometheus client)

## Performance Considerations

- **Batch Processing**: Track all workspaces in a single call
- **Connection Pooling**: MongoDB client manages connection pool
- **Caching**: Carbon intensity cached for duplicate timestamps
- **Async Support**: Use separate tracker instances for parallel processing

## Integration Example

Complete example integrating all components:

```python
from workspace_tracking import WorkspaceTracker
from datetime import datetime, timedelta

# Initialize
tracker = WorkspaceTracker(
    mongo_uri="mongodb://localhost:27017/",
    mongo_db="ada",
    prometheus_url="https://prometheus.example.com/",
    default_cpu_tdp_w=100.0
)

try:
    # Track workspaces every hour
    for hour in range(24):
        timestamp = datetime.now() - timedelta(hours=hour)

        tracked = tracker.track_all_active_workspaces(
            timestamp=timestamp,
            cloud_project_name="CDAaaS",
            machine_name="MUON"
        )

        print(f"Hour {hour}: Tracked {len(tracked)} workspaces")

    # Get summary
    summary = tracker.get_summary_statistics()

    # Export results
    tracker.export_to_json("workspace_usage_24h.json")

    print(f"\n24-Hour Summary:")
    print(f"Total Energy: {summary['total_energy_kwh']:.2f} kWh")
    print(f"Total Carbon: {summary['total_carbon_gco2eq']:.2f} gCO2eq")

finally:
    tracker.close()
```

## License

See main project LICENSE file.
