---
title: Database Structure
parent: Backend
nav_order: 1
---

# Database Structure

The carbon monitoring system uses the existing Ada MongoDB database through `ada-db-interface`. This integrates directly with the Ada platform's data without maintaining a separate database.

## Architecture

```
ada-carbon-monitoring-api
    |
    v
ada-db-interface (REST API)
    |
    v
MongoDB (Ada platform database)
```

## Collections

### workspaces

Active and historical workspace records.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `hostname` | string | Machine hostname |
| `owner` | string | Platform name of workspace owner |
| `state` | string | READY, CLAIMED, DELETED, etc. |
| `tag` | string | Platform tag (ISIS, CLF, TRAINING, etc.) |
| `created_time` | datetime | When workspace was created |
| `deleted_time` | datetime | When workspace was deleted (null if active) |
| `parameters.users` | array | List of users with access |

**Example Document:**

```json
{
  "_id": "abc123",
  "hostname": "workspace-abc123-muon-0",
  "owner": "jb1234567",
  "state": "READY",
  "tag": "ISIS",
  "created_time": "2025-06-01T10:00:00Z",
  "deleted_time": null,
  "parameters": {
    "users": [
      {"platform_name": "jb1234567", "access": "owner"}
    ]
  }
}
```

### users

User information.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `platform_name` | string | Platform login name |
| `name` | string | Full name |
| `email` | string | Email address |
| `uid` | integer | Unix UID |

### groups

Experiment and group records.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `name` | string | Group name (e.g., RB number) |
| `gid` | integer | Group ID |
| `type` | string | Group type |
| `members` | array | List of member information |

### hosts

Host and machine information.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `hostname` | string | Machine hostname |
| `cloud_project_name` | string | IDAaaS, CDAaaS, etc. |
| `machine_name` | string | Muon, Laser, Analysis, etc. |

### specifications

Workspace specification definitions.

**Key Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Unique identifier |
| `name` | string | Specification name |
| `cpus` | integer | Number of CPUs |
| `memory` | integer | Memory in MB |
| `tag` | string | Platform tag |

## Querying via ada-db-interface

The carbon monitoring API queries MongoDB through the ada-db-interface REST API.

### Get Active Workspaces

```bash
GET /workspaces?where={"state":{"$in":["READY","CLAIMED"]}}
```

### Get Workspaces by Owner

```bash
GET /workspaces?where={"owner":"jb1234567"}
```

### Get Workspaces by Tag

```bash
GET /workspaces?where={"tag":"ISIS"}
```

### Get User by Platform Name

```bash
GET /users?where={"platform_name":"jb1234567"}
```

## Tag to Cloud Project Mapping

| Tag | Cloud Project |
|-----|---------------|
| ISIS | IDAaaS |
| CLF | CDAaaS |
| TRAINING | IDAaaS |
| DEV | DDAaaS |
| AI4Science | IDAaaS |

## Data Flow for Carbon Calculation

1. **Get active workspaces** from MongoDB via ada-db-interface
2. **Extract hostnames** from workspace records
3. **Query Prometheus** for CPU metrics by hostname
4. **Calculate electricity** from CPU seconds
5. **Get carbon intensity** from UK Carbon Intensity API
6. **Calculate carbon footprint** from electricity and intensity
7. **Attribute to user** based on workspace owner

## Configuration

ada-carbon-monitoring-api connects to ada-db-interface via configuration:

```ini
[REGISTER]
url = http://localhost:5002
username = admin
password = admin
timeout = 30
pagination_limit = 500
```

Or via environment variables:

```bash
REGISTER_URL=http://localhost:5002
REGISTER_USERNAME=admin
REGISTER_PASSWORD=admin
REGISTER_TIMEOUT=30
```
