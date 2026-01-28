---
title: User Attribution
parent: Usage Estimation
nav_order: 6
---

# User Attribution

User attribution connects CPU usage data from Prometheus to the Ada platform users who generated that usage.

## How It Works

### 1. CPU Usage Data (Prometheus)

Prometheus stores CPU metrics with the following labels:
- `cloud_project_name`: The OpenStack project (e.g., "IDAaaS", "CDAaaS")
- `machine_name`: The machine type (e.g., "MUON", "Artemis (Matlab)")
- `host`: The hostname/IP of the workspace

### 2. Workspace Records (MongoDB)

Ada's MongoDB stores workspace records with:
- `hostname`: The workspace's IP address
- `owner`: The user's platform name
- `created_time`: When the workspace was created
- `deleted_time`: When the workspace was deleted (if applicable)
- `state`: Current state (READY, CLAIMED, DELETED, etc.)

### 3. Matching Algorithm

To attribute CPU usage to a user:

```python
def get_user_by_host_and_time(hostname: str, timestamp: datetime) -> User:
    """
    Find the user who owned the workspace at a given time.

    1. Find workspace with matching hostname
    2. Check if timestamp falls within workspace's active period
    3. Return the workspace owner's user record
    """
    workspace = workspaces.find_one({
        "hostname": hostname,
        "created_time": {"$lte": timestamp},
        "$or": [
            {"deleted_time": None},
            {"deleted_time": {"$gt": timestamp}}
        ]
    })

    if workspace:
        return users.find_one({"platform_name": workspace["owner"]})
    return None
```

## Attribution Flow

```
Prometheus metric:
  node_cpu_seconds_total{host="172.16.100.50", ...}
                ↓
MongoDB query:
  workspaces.find({hostname: "172.16.100.50", ...})
                ↓
User lookup:
  users.find({platform_name: workspace.owner})
                ↓
Result: User attribution with carbon data
```

## Implementation in ada-carbon-monitoring-api

The `WorkspaceTracker` class handles attribution:

```python
from src.clients.mongodb_client import MongoDBClient
from src.clients.prometheus_client import PrometheusAPIClient

class WorkspaceTracker:
    def track_workspace(self, workspace: dict, timestamp: datetime):
        # 1. Get workspace owner
        owner = workspace.get("owner")

        # 2. Look up user details
        user = self.mongo_client.get_user_by_platform_name(owner)

        # 3. Get CPU usage from Prometheus
        hostname = workspace.get("hostname")
        cpu_data = self.prometheus_client.get_cpu_usage_breakdown(
            timestamp=timestamp,
            host=hostname
        )

        # 4. Calculate carbon and create attribution
        return WorkspaceUsageEntry(
            workspace_id=str(workspace["_id"]),
            hostname=hostname,
            owner=owner,
            user_info=user,
            cpu_usage=cpu_data,
            # ... carbon calculations
        )
```

## User Data Structure

MongoDB user documents contain:

```json
{
    "_id": ObjectId("..."),
    "platform_name": "aa123456",
    "uid": 100001,
    "gid": 111111,
    "auth_providers": {
        "iris_iam": "aa123456@iris.ac.uk"
    },
    "tag": "ISIS",
    "name": "Andrew Smith",
    "email": "andrew.smith@stfc.ac.uk",
    "parameters": {
        "last_login": ISODate("2026-01-28T10:00:00Z")
    }
}
```

## API Endpoint

The `/workspaces/track` endpoint returns attributed usage:

```bash
curl -X POST "http://localhost:8000/workspaces/track" \
  -H "Content-Type: application/json" \
  -d '{"cloud_project_name": "IDAaaS"}'
```

Response includes user attribution:

```json
{
    "tracked_count": 8,
    "workspaces": [
        {
            "workspace_id": "...",
            "hostname": "172.16.100.50",
            "owner": "aa123456",
            "user_info": {
                "platform_name": "aa123456",
                "name": "Andrew Smith",
                "email": "andrew.smith@stfc.ac.uk",
                "uid": 100001
            },
            "cpu_usage": {...},
            "carbon_gco2eq": {...}
        }
    ]
}
```

## Edge Cases

### Unattributable Usage

Some CPU usage cannot be attributed to specific users:
- System processes on shared infrastructure
- Pool workspaces not yet claimed
- Usage during workspace creation/deletion

This usage is tracked at the project/machine level rather than user level.

### Multiple Users Over Time

A single host may serve multiple users over its lifetime:
- Workspace created by User A at 09:00
- Deleted at 12:00
- New workspace created by User B at 13:00

The timestamp-based matching ensures correct attribution.
