---
title: Usage
parent: SQLite Class
nav_order: 2
---

# Quickstart

```python
from usage_db import UsageDB  # wherever you put the class

# 1) Create / open a database (file-backed or in-memory)
db = UsageDB(path="usage.db")   # or ":memory:" for ephemeral

# 2) Seed some reference data
group_id   = db.get_or_create_group("Research")
user_id    = db.get_or_create_user("u123", display_name="Ada Lovelace", group_name="Research")
project_id = db.get_or_create_project("alpha-cloud")
machine_id = db.get_or_create_machine("gpu-01")

# 3) Map relationships (many-to-many helpers)
db.map_user_project(user_id="u123", cloud_project_name="alpha-cloud")
db.map_project_machine(cloud_project_name="alpha-cloud", machine_name="gpu-01")

# 4) Register a running workspace (optional)
instance_id = db.get_or_create_instance(host="10.0.0.5", port=2222, raw_label="gpu-01:2222")
ws_id = db.start_workspace(
    instance_id=instance_id,
    machine_id=machine_id,
    user_id="u123",
    project_id=project_id,
    started_at_iso_utc="2025-10-01T09:00:00Z",
)
```

---

# Insert usage (single rows)

Each row goes into one of the four scopes: `"ada"`, `"project"`, `"machine"`, or `"user"`.
Only the ID required by that scope may be set (the class validates this and the DB enforces it).

```python
# ADA scope (platform-wide, no IDs)
db.insert_fact_usage(
    scope="ada",
    ts_iso_utc="2025-10-01T00:00:00Z",
    busy_kwh=12.5, idle_kwh=3.0, busy_gCo2eq=2300, idle_gCo2eq=500
)

# PROJECT scope (only project_id allowed)
db.insert_fact_usage(
    scope="project",
    ts_iso_utc="2025-10-01T00:00:00Z",
    project_id=project_id,
    busy_kwh=9.1, idle_kwh=1.2, busy_gCo2eq=1700, idle_gCo2eq=210
)

# MACHINE scope (only machine_id allowed)
db.insert_fact_usage(
    scope="machine",
    ts_iso_utc="2025-10-01T00:00:00Z",
    machine_id=machine_id,
    busy_cpu_seconds_total=18_000, idle_cpu_seconds_total=6_000,
    busy_kwh=5.4, idle_kwh=0.9, busy_gCo2eq=1000, idle_gCo2eq=160
)

# USER scope (only user_id allowed)
db.insert_fact_usage(
    scope="user",
    ts_iso_utc="2025-10-01T00:00:00Z",
    user_id="u123",
    busy_kwh=3.3, idle_kwh=0.4, busy_gCo2eq=610, idle_gCo2eq=70
)
```

### Upsert behavior (idempotent writes)

If you insert again with the same (scope, ts, ids), it **updates** that row:

```python
# Will update the existing project record at the same timestamp
db.insert_fact_usage(
    scope="project",
    ts_iso_utc="2025-10-01T00:00:00Z",
    project_id=project_id,
    busy_kwh=10.0, idle_kwh=1.0, busy_gCo2eq=1800, idle_gCo2eq=200
)
```

### Validation example (what NOT to do)

```python
try:
    # ❌ machine_id must be NULL for scope='project' → raises ValueError
    db.insert_fact_usage(scope="project", ts_iso_utc="2025-10-01T01:00:00Z",
                         project_id=project_id, machine_id=machine_id)
except ValueError as e:
    print("Validation error:", e)
```

---

# Bulk insert

```python
rows = [
    dict(scope="project", ts_iso_utc="2025-10-01T01:00:00Z",
         project_id=project_id, busy_kwh=7.0, idle_kwh=1.0, busy_gCo2eq=1200, idle_gCo2eq=190),

    dict(scope="machine", ts_iso_utc="2025-10-01T01:00:00Z",
         machine_id=machine_id, busy_cpu_seconds_total=19_000, idle_cpu_seconds_total=5_000,
         busy_kwh=5.7, idle_kwh=0.7, busy_gCo2eq=1040, idle_gCo2eq=120),

    dict(scope="user", ts_iso_utc="2025-10-01T01:00:00Z",
         user_id="u123", busy_kwh=3.0, idle_kwh=0.3, busy_gCo2eq=560, idle_gCo2eq=60),
]
db.bulk_insert_fact_usage(rows)
```

---

# Read time-series

```python
db.ada_timeseries()                     # → [{ts, busy_kwh, idle_kwh, ..., intensity_gCo2eq_kwh}, ...]
db.project_timeseries("alpha-cloud")    # → rows for that project
db.machine_timeseries("gpu-01")         # → rows for that machine
db.user_timeseries("u123")              # → rows for that user
```

---

# Totals & Averages

```python
db.project_totals()     # → energy/carbon totals per project
db.machine_totals()     # → totals per machine
db.group_totals()       # → totals per user group (from user-scoped data)
db.user_totals()        # → totals per user

db.project_averages()   # → per-project averages across the series
db.machine_averages()
db.group_averages()
db.user_averages()
```

---

# Convenience views

```python
db.active_workspaces()
# → [{workspace_id, started_at, user, project, machine, host, port}, ...]

db.user_project_memberships()
# → [{user_id, display_name, group_name, cloud_project_name}, ...]
```

---

# Analytics “cookbook” helpers

```python
# Energy & carbon by project in a window
db.project_energy_carbon_between("2025-10-01T00:00:00Z", "2025-10-02T00:00:00Z")

# Top-N groups by energy in a window
db.top_groups_by_energy("2025-10-01T00:00:00Z", "2025-10-02T00:00:00Z", n=5)

# Machine carbon-intensity over time
db.machine_intensity_trend("gpu-01")

# User contributions to projects in a window
db.user_contribution_window("2025-10-01T00:00:00Z", "2025-10-02T00:00:00Z")

# Busy/idle CPU share per machine in a window
db.machine_utilization_share("2025-10-01T00:00:00Z", "2025-10-02T00:00:00Z")
```

---

# Custom SQL (escape hatch)

```python
# Anything the views expose can be queried directly
top_projects = db.q("""
    SELECT cloud_project_name, busy_kwh + idle_kwh AS energy_kwh
    FROM v_project_totals
    ORDER BY energy_kwh DESC
    LIMIT 10
""")
```

---

# Transactions 

```python
from datetime import datetime, timezone

ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

try:
    with db.transaction():
        db.insert_fact_usage(scope="ada", ts_iso_utc=ts, busy_kwh=1.0, idle_kwh=0.2)
        db.insert_fact_usage(scope="project", ts_iso_utc=ts, project_id=project_id, busy_kwh=0.8)
        # Any exception here will roll back both inserts
except Exception as e:
    print("Rolled back due to:", e)
```

---

---

# Cleanup

```python
db.close()
```

