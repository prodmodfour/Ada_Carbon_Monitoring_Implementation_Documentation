---
title: Group Attribution
parent: Usage Estimation
nav_order: 5
---

# Group Attribution

Group attribution aggregates carbon usage by machine type and cloud project, enabling facility-level carbon reporting.

## What is a Group?

In the Ada carbon monitoring system, a **group** is the combination of:
- **cloud_project_name** - The OpenStack project (e.g., "IDAaaS", "CDAaaS")
- **machine_name** - The machine type (e.g., "Muon", "SANS", "Tomography")

This combination identifies all workspaces of a particular type within a facility.

### Group Name Format

Groups are named as: `{cloud_project}_{machine_name}`

**Examples:**
- `IDAaaS_Muon` - ISIS Muon workspaces
- `IDAaaS_SANS` - ISIS SANS workspaces
- `CDAaaS_Tomography` - CLF Tomography workspaces

## API Endpoints

### List All Groups

```bash
GET /groups
```

**Response:**
```json
{
  "groups": [
    {"name": "IDAaaS_Muon", "cloud_project": "IDAaaS", "machine_name": "Muon"},
    {"name": "IDAaaS_SANS", "cloud_project": "IDAaaS", "machine_name": "SANS"},
    {"name": "CDAaaS_Tomography", "cloud_project": "CDAaaS", "machine_name": "Tomography"}
  ],
  "count": 780
}
```

### Get Group Carbon Usage

```bash
GET /groups/{group_name}/usage
```

**Example:**
```bash
curl http://localhost:8000/groups/IDAaaS_Muon/usage
```

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
    "carbon_intensity_g_per_kwh": 231.5,
    "status": "processed"
  }
]
```

### Get Group Carbon Summary

```bash
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
    "top_equivalencies": {
      "smartphone_charges": {"value": 2.3, "unit": "charges"},
      "streaming_hours": {"value": 0.34, "unit": "hours"}
    }
  }
}
```

## Implementation

### WorkspaceTracker.track_group()

The `track_group` method queries Prometheus for all hosts in a group:

```python
def track_group(
    self,
    cloud_project_name: str,
    machine_name: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> Optional[WorkspaceUsageEntry]:
    """
    Track carbon usage for a group (cloud_project + machine_name).

    Unlike track_workspace which tracks individual hosts, this method
    aggregates all usage for a cloud project and machine type combination.
    """
    group_name = f"{cloud_project_name}_{machine_name}"

    # Create entry for the group
    entry = WorkspaceUsageEntry(
        workspace_id=group_name,
        hostname=group_name,
        owner=None
    )
    entry.set_timestamp(timestamp)

    # Query Prometheus WITHOUT host filter - gets all hosts in group
    cpu_data = self.prometheus_client.get_cpu_usage_breakdown(
        timestamp=timestamp,
        cloud_project_name=cloud_project_name,
        machine_name=machine_name,
        host=None  # No host filter = aggregate all
    )

    if cpu_data:
        # Calculate energy and carbon...
        entry.set_cpu_seconds_total(cpu_data["busy"], cpu_data["idle"])
        # ... rest of calculation

    return entry
```

### Prometheus Query

Group queries use the same metric but without the `instance` filter:

```promql
# Individual workspace
increase(node_cpu_seconds_total{
    cloud_project_name="IDAaaS",
    machine_name="Muon",
    instance=~"172.16.100.50.*"
}[1h])

# Group (all workspaces of this type)
increase(node_cpu_seconds_total{
    cloud_project_name="IDAaaS",
    machine_name="Muon"
}[1h])
```

## Prometheus Labels

The group identification relies on Prometheus labels:

| Label | Description | Example |
|-------|-------------|---------|
| `cloud_project_name` | OpenStack project | "IDAaaS", "CDAaaS" |
| `machine_name` | Machine type | "Muon", "SANS", "Tomography" |
| `instance` | Host IP/hostname | "172.16.100.50:9100" |

### Label to Facility Mapping

| cloud_project_name | Facility |
|--------------------|----------|
| IDAaaS | ISIS |
| CDAaaS | CLF |
| DDAaaS | Development |
| TDAaaS | Training |

## Use Cases

### Facility Reporting

Generate monthly carbon reports per instrument:

```python
# Get all ISIS Muon carbon for January 2026
summary = tracker.track_group(
    cloud_project_name="IDAaaS",
    machine_name="Muon",
    timestamp=datetime(2026, 1, 31)
)
print(f"ISIS Muon: {summary.total_usage_gco2eq:.2f} gCO2eq")
```

### Cross-Facility Comparison

Compare carbon across facilities:

```python
facilities = ["IDAaaS", "CDAaaS"]
for facility in facilities:
    summary = tracker.track_group(cloud_project_name=facility)
    print(f"{facility}: {summary.total_usage_gco2eq:.2f} gCO2eq")
```

### Instrument Efficiency Analysis

Identify high-carbon instruments:

```python
groups = get_all_groups()
usage = []
for group in groups:
    summary = tracker.track_group(
        cloud_project_name=group.cloud_project,
        machine_name=group.machine_name
    )
    usage.append((group.name, summary.total_usage_gco2eq))

# Sort by carbon usage
usage.sort(key=lambda x: x[1], reverse=True)
print("Top 5 carbon-intensive groups:")
for name, carbon in usage[:5]:
    print(f"  {name}: {carbon:.2f} gCO2eq")
```

## MongoDB Groups Collection

In addition to Prometheus-based groups, MongoDB stores experiment groups:

```json
{
    "_id": ObjectId("..."),
    "name": "RB2024001",
    "gid": 200001,
    "tag": "ISIS",
    "members": ["aa123456", "bb234567"],
    "type": "experiment",
    "parameters": {
        "title": "Neutron Diffraction Study",
        "pi": "aa123456",
        "instrument": "WISH"
    }
}
```

These can be used for:
- Attributing carbon to specific experiments (by matching instrument and time period)
- Generating per-experiment carbon reports
- Tracking carbon per PI or research group

## Relationship to User Attribution

| Attribution Type | Scope | Use Case |
|-----------------|-------|----------|
| User | Individual workspaces owned by a user | Personal carbon tracking |
| Group | All workspaces of a machine type | Facility/instrument reporting |
| Experiment | Workspaces used during an experiment | Research project carbon |

Users belong to groups, and groups contribute to facility totals:

```
Facility (IDAaaS)
├── Group (Muon)
│   ├── User A's workspace (5 gCO2eq)
│   └── User B's workspace (3 gCO2eq)
│   Total: 8 gCO2eq
├── Group (SANS)
│   └── User C's workspace (10 gCO2eq)
│   Total: 10 gCO2eq
Total: 18 gCO2eq
```
