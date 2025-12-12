# MongoDB Client for Ada Carbon Monitoring

## Overview

The `MongoDBClient` class provides an interface to query the Ada MongoDB database to attribute Prometheus usage data to specific users and groups. This enables accurate tracking of resource consumption and carbon footprint attribution.

## Architecture

The client works by combining data from multiple MongoDB collections:

1. **Workspaces Collection**: Tracks which user had control of which host at what time
   - `hostname`: The host identifier
   - `owner`: Platform name of the user
   - `created_time`: When the workspace was created
   - `acquired_time`: When the workspace was acquired by the user
   - `deleted_time`: When the workspace was deleted

2. **Users Collection**: Contains user information
   - `platform_name`: Unique user identifier
   - `name`: Full name
   - `email`: Email address
   - `uid`: User ID

3. **Groups Collection**: Contains group information
   - `name`: Group name (format: `{cloud_project_name}_{machine_name}`)
   - `gid`: Group ID
   - `members`: List of member platform names
   - `type`: Group type

## Installation

Ensure pymongo is installed:

```bash
pip install pymongo[srv]==4.6.3
```

## Usage

### Basic Connection

```python
from mongodb.MongoDBClient import MongoDBClient

# Connect without authentication
client = MongoDBClient(
    mongo_uri="mongodb://localhost:27017/",
    database_name="ada"
)

# Connect with authentication
client = MongoDBClient(
    mongo_uri="mongodb://localhost:27017/",
    database_name="ada",
    username="your_username",
    password="your_password"
)
```

### Find User by Host and Time

```python
from datetime import datetime

user = client.get_user_by_host_and_time(
    hostname="172.16.100.50",
    timestamp=datetime(2025, 9, 23, 17, 0, 0)
)

if user:
    print(f"User: {user['platform_name']}")
    print(f"Name: {user['name']}")
    print(f"Email: {user['email']}")
```

### Find Group by Cloud Project and Machine

```python
group = client.get_group_by_cloud_project_and_machine(
    cloud_project_name="CDAaaS",
    machine_name="MUON"
)

if group:
    print(f"Group: {group['name']}")
    print(f"Members: {group['members']}")
```

### Attribute Usage to User

```python
attribution = client.attribute_usage_to_user(
    hostname="172.16.100.50",
    timestamp=datetime(2025, 9, 23, 17, 0, 0),
    cpu_usage=3600.0,  # CPU seconds
    additional_metrics={
        "memory_usage_mb": 8192,
        "carbon_intensity": 45.2,
        "energy_kwh": 2.5
    }
)

if attribution:
    print(f"User: {attribution['user']['platform_name']}")
    print(f"CPU Usage: {attribution['usage']['cpu_usage_seconds']} seconds")
    print(f"Carbon Intensity: {attribution['usage']['carbon_intensity']} gCO2/kWh")
```

### Attribute Usage to Group

```python
attribution = client.attribute_usage_to_group(
    cloud_project_name="CDAaaS",
    machine_name="MUON",
    timestamp=datetime(2025, 9, 23, 17, 0, 0),
    cpu_usage=7200.0,
    additional_metrics={
        "memory_usage_mb": 16384,
        "carbon_intensity": 45.2
    }
)

if attribution:
    print(f"Group: {attribution['group']['name']}")
    print(f"CPU Usage: {attribution['usage']['cpu_usage_seconds']} seconds")
```

### Integration with Prometheus Client

```python
from mongodb.MongoDBClient import MongoDBClient
from prometheus.PrometheusAPIClient import PrometheusAPIClient
from datetime import datetime

# Initialize clients
mongo_client = MongoDBClient(
    mongo_uri="mongodb://localhost:27017/",
    database_name="ada"
)

prom_client = PrometheusAPIClient(
    prometheus_url="https://host-172-16-100-248.nubes.stfc.ac.uk/"
)

# Get CPU usage from Prometheus
timestamp = datetime(2025, 9, 23, 17, 0, 0)
prom_data = prom_client.cpu_seconds_total(
    timestamp=timestamp,
    cloud_project_name="CDAaaS",
    machine_name="MUON",
    host="172.16.100.50"
)

# Extract CPU usage value from Prometheus response
if prom_data and prom_data.get('status') == 'success':
    cpu_usage = float(prom_data['data']['result'][0]['value'][1])

    # Attribute to user
    attribution = mongo_client.attribute_usage_to_user(
        hostname="172.16.100.50",
        timestamp=timestamp,
        cpu_usage=cpu_usage
    )

    if attribution:
        print(f"Attributed {cpu_usage}s CPU to user {attribution['user']['platform_name']}")

# Always close connections
mongo_client.close()
```

## API Reference

### MongoDBClient

#### `__init__(mongo_uri, database_name, username=None, password=None)`
Initialize MongoDB connection.

**Parameters:**
- `mongo_uri` (str): MongoDB connection URI
- `database_name` (str): Database name
- `username` (str, optional): Username for authentication
- `password` (str, optional): Password for authentication

#### `get_user_by_host_and_time(hostname, timestamp)`
Find user who controlled a host at a specific time.

**Parameters:**
- `hostname` (str): The hostname
- `timestamp` (datetime): The datetime to query

**Returns:** User document dict or None

#### `get_group_by_cloud_project_and_machine(cloud_project_name, machine_name)`
Find group by cloud project and machine name.

**Parameters:**
- `cloud_project_name` (str): Cloud project name
- `machine_name` (str): Machine name

**Returns:** Group document dict or None

#### `attribute_usage_to_user(hostname, timestamp, cpu_usage, additional_metrics=None)`
Attribute usage metrics to a user.

**Parameters:**
- `hostname` (str): The hostname
- `timestamp` (datetime): When usage occurred
- `cpu_usage` (float): CPU usage in seconds
- `additional_metrics` (dict, optional): Additional metrics to include

**Returns:** Attribution dict with user and usage info, or None

#### `attribute_usage_to_group(cloud_project_name, machine_name, timestamp, cpu_usage, additional_metrics=None)`
Attribute usage metrics to a group.

**Parameters:**
- `cloud_project_name` (str): Cloud project name
- `machine_name` (str): Machine name
- `timestamp` (datetime): When usage occurred
- `cpu_usage` (float): CPU usage in seconds
- `additional_metrics` (dict, optional): Additional metrics to include

**Returns:** Attribution dict with group and usage info, or None

#### `get_all_groups_for_cloud_project(cloud_project_name)`
Get all groups for a cloud project.

**Parameters:**
- `cloud_project_name` (str): Cloud project name

**Returns:** List of group documents

#### `get_user_by_platform_name(platform_name)`
Get user by platform name.

**Parameters:**
- `platform_name` (str): User's platform name

**Returns:** User document dict or None

#### `get_workspaces_by_hostname(hostname, start_time=None, end_time=None)`
Get workspaces for a hostname with optional time filtering.

**Parameters:**
- `hostname` (str): The hostname
- `start_time` (datetime, optional): Filter start time
- `end_time` (datetime, optional): Filter end time

**Returns:** List of workspace documents

#### `close()`
Close MongoDB connection.

## Error Handling

The client includes comprehensive error handling:
- Connection failures are logged and raised
- Query failures return None and log errors
- All database operations are wrapped in try-except blocks

## Best Practices

1. **Always close connections**: Use `client.close()` or context managers
2. **Handle None returns**: Check if queries return None before using results
3. **Time zones**: Ensure timestamps are timezone-aware for accurate matching
4. **Caching**: Consider caching frequently accessed data
5. **Connection pooling**: MongoDB driver handles connection pooling automatically

## License

See main project LICENSE file.
