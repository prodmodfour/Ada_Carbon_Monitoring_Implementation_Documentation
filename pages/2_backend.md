---
title: Backend
nav_order: 4    
nav_exclude: false     
---

# Database Structure
## SQL Tables and Views
```sql
-- === Dimension tables ===

CREATE TABLE dim_group (
  group_id     INTEGER PRIMARY KEY,
  group_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_user (
  user_id      TEXT PRIMARY KEY,          -- you already have string user IDs
  display_name TEXT,
  group_id     INTEGER REFERENCES dim_group(group_id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE dim_project (
  project_id           INTEGER PRIMARY KEY,
  cloud_project_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_machine (
  machine_id   INTEGER PRIMARY KEY,
  machine_name TEXT NOT NULL UNIQUE
);

-- Many-to-many helpers (optional but useful)
CREATE TABLE map_user_project (
  user_id    TEXT    NOT NULL REFERENCES dim_user(user_id)    ON DELETE CASCADE,
  project_id INTEGER NOT NULL REFERENCES dim_project(project_id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, project_id)
);

CREATE TABLE map_project_machine (
  project_id INTEGER NOT NULL REFERENCES dim_project(project_id) ON DELETE CASCADE,
  machine_id INTEGER NOT NULL REFERENCES dim_machine(machine_id) ON DELETE CASCADE,
  PRIMARY KEY (project_id, machine_id)
);

-- Optional: break out “instance=host:port” cleanly
CREATE TABLE dim_instance (
  instance_id INTEGER PRIMARY KEY,
  host        TEXT NOT NULL,
  port        INTEGER,
  raw_label   TEXT        -- original string if you want to keep it
);

-- === Fact tables ===
-- Single flexible timeseries for *all* scopes (Ada, Project, Machine, User)

CREATE TABLE fact_usage (
  usage_id     INTEGER PRIMARY KEY,
  ts           TEXT    NOT NULL,      -- ISO-8601 UTC (e.g. 2025-09-11T10:30:00Z)
  scope        TEXT    NOT NULL CHECK (scope IN ('ada','project','machine','user')),
  project_id   INTEGER REFERENCES dim_project(project_id),
  machine_id   INTEGER REFERENCES dim_machine(machine_id),
  user_id      TEXT    REFERENCES dim_user(user_id),

  busy_cpu_seconds_total REAL NOT NULL DEFAULT 0.0,
  idle_cpu_seconds_total REAL NOT NULL DEFAULT 0.0,
  busy_kwh               REAL NOT NULL DEFAULT 0.0,
  idle_kwh               REAL NOT NULL DEFAULT 0.0,
  busy_gCo2eq            REAL NOT NULL DEFAULT 0.0,
  idle_gCo2eq            REAL NOT NULL DEFAULT 0.0,
  intensity_gCo2eq_kwh   REAL,          -- optional override; can be computed in views

  -- Ensure the right keys are present for each scope
  CHECK ( (scope='ada'     AND project_id IS NULL AND machine_id IS NULL AND user_id IS NULL)
       OR (scope='project' AND project_id IS NOT NULL AND machine_id IS NULL AND user_id IS NULL)
       OR (scope='machine' AND machine_id IS NOT NULL AND project_id IS NULL AND user_id IS NULL)
       OR (scope='user'    AND user_id    IS NOT NULL AND project_id IS NULL AND machine_id IS NULL)
  ),

  -- Uniqueness per timeseries grain
  UNIQUE (scope, ts, COALESCE(project_id, -1), COALESCE(machine_id, -1), COALESCE(user_id, ''))
);

CREATE INDEX idx_fact_usage_ts       ON fact_usage(ts);
CREATE INDEX idx_fact_usage_scope    ON fact_usage(scope);
CREATE INDEX idx_fact_usage_project  ON fact_usage(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_fact_usage_machine  ON fact_usage(machine_id) WHERE machine_id IS NOT NULL;
CREATE INDEX idx_fact_usage_user     ON fact_usage(user_id)    WHERE user_id IS NOT NULL;

-- Active workspaces (normalized)
CREATE TABLE active_workspace (
  workspace_id INTEGER PRIMARY KEY,
  instance_id  INTEGER NOT NULL REFERENCES dim_instance(instance_id),
  machine_id   INTEGER NOT NULL REFERENCES dim_machine(machine_id),
  user_id      TEXT REFERENCES dim_user(user_id),
  project_id   INTEGER REFERENCES dim_project(project_id),
  started_at   TEXT  NOT NULL   -- ISO-8601 UTC
  -- Note: per-workspace energy/carbon shouldn’t live here; they belong in fact_usage
);

-- === Derived “Totals” and “Averages” as VIEWS ===
-- Ada total timeseries (unchanged semantics, now just a slice)
CREATE VIEW v_ada_timeseries AS
SELECT
  ts,
  busy_cpu_seconds_total,
  idle_cpu_seconds_total,
  busy_kwh,
  idle_kwh,
  busy_gCo2eq,
  idle_gCo2eq,
  CASE
    WHEN (busy_kwh + idle_kwh) > 0
    THEN (busy_gCo2eq + idle_gCo2eq) / (busy_kwh + idle_kwh)
    ELSE NULL
  END AS intensity_gCo2eq_kwh
FROM fact_usage
WHERE scope='ada';

-- Cloud project usage timeseries
CREATE VIEW v_project_timeseries AS
SELECT
  p.cloud_project_name,
  f.ts,
  f.busy_cpu_seconds_total,
  f.idle_cpu_seconds_total,
  f.busy_kwh,
  f.idle_kwh,
  f.busy_gCo2eq,
  f.idle_gCo2eq,
  COALESCE(f.intensity_gCo2eq_kwh,
           CASE WHEN (f.busy_kwh + f.idle_kwh) > 0
                THEN (f.busy_gCo2eq + f.idle_gCo2eq)/(f.busy_kwh + f.idle_kwh)
           END) AS intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_project p ON p.project_id = f.project_id
WHERE f.scope='project';

-- Machine usage timeseries
CREATE VIEW v_machine_timeseries AS
SELECT
  m.machine_name,
  f.ts,
  f.busy_cpu_seconds_total,
  f.idle_cpu_seconds_total,
  f.busy_kwh,
  f.idle_kwh,
  f.busy_gCo2eq,
  f.idle_gCo2eq,
  COALESCE(f.intensity_gCo2eq_kwh,
           CASE WHEN (f.busy_kwh + f.idle_kwh) > 0
                THEN (f.busy_gCo2eq + f.idle_gCo2eq)/(f.busy_kwh + f.idle_kwh)
           END) AS intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_machine m ON m.machine_id = f.machine_id
WHERE f.scope='machine';

-- User usage timeseries
CREATE VIEW v_user_timeseries AS
SELECT
  u.user_id,
  f.ts,
  f.busy_cpu_seconds_total,
  f.idle_cpu_seconds_total,
  f.busy_kwh,
  f.idle_kwh,
  f.busy_gCo2eq,
  f.idle_gCo2eq,
  COALESCE(f.intensity_gCo2eq_kwh,
           CASE WHEN (f.busy_kwh + f.idle_kwh) > 0
                THEN (f.busy_gCo2eq + f.idle_gCo2eq)/(f.busy_kwh + f.idle_kwh)
           END) AS intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_user u ON u.user_id = f.user_id
WHERE f.scope='user';

-- Project / Machine / Group / User Totals (sums)
CREATE VIEW v_project_totals AS
SELECT
  p.cloud_project_name,
  SUM(busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(busy_kwh)              AS busy_kwh,
  SUM(idle_kwh)              AS idle_kwh,
  SUM(busy_gCo2eq)           AS busy_gCo2eq,
  SUM(idle_gCo2eq)           AS idle_gCo2eq
FROM fact_usage f
JOIN dim_project p ON p.project_id = f.project_id
WHERE f.scope='project'
GROUP BY p.cloud_project_name;

CREATE VIEW v_machine_totals AS
SELECT
  m.machine_name,
  SUM(busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(busy_kwh)              AS busy_kwh,
  SUM(idle_kwh)              AS idle_kwh,
  SUM(busy_gCo2eq)           AS busy_gCo2eq,
  SUM(idle_gCo2eq)           AS idle_gCo2eq
FROM fact_usage f
JOIN dim_machine m ON m.machine_id = f.machine_id
WHERE f.scope='machine'
GROUP BY m.machine_name;

CREATE VIEW v_group_totals AS
SELECT
  g.group_name,
  SUM(f.busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(f.idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(f.busy_kwh)               AS busy_kwh,
  SUM(f.idle_kwh)               AS idle_kwh,
  SUM(f.busy_gCo2eq)            AS busy_gCo2eq,
  SUM(f.idle_gCo2eq)            AS idle_gCo2eq
FROM fact_usage f
JOIN dim_user u ON u.user_id = f.user_id
JOIN dim_group g ON g.group_id = u.group_id
WHERE f.scope='user'
GROUP BY g.group_name;

CREATE VIEW v_user_totals AS
SELECT
  u.user_id,
  SUM(busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(busy_kwh)               AS busy_kwh,
  SUM(idle_kwh)               AS idle_kwh,
  SUM(busy_gCo2eq)            AS busy_gCo2eq,
  SUM(idle_gCo2eq)            AS idle_gCo2eq
FROM fact_usage f
JOIN dim_user u ON u.user_id = f.user_id
WHERE f.scope='user'
GROUP BY u.user_id;

-- “Averages” (flattening the JSON blocks)
-- Here “average” is the arithmetic mean across rows in the chosen timeseries.
-- If you want a time-weighted mean, switch AVG(...) to SUM(...)/SUM(duration).

CREATE VIEW v_project_averages AS
SELECT
  p.cloud_project_name,
  AVG(busy_kwh)  AS avg_busy_energy_kwh,
  AVG(idle_kwh)  AS avg_idle_energy_kwh,
  AVG(busy_gCo2eq) AS avg_busy_carbon_gCo2eq,
  AVG(idle_gCo2eq) AS avg_idle_carbon_gCo2eq,
  AVG(
    CASE WHEN (busy_kwh + idle_kwh) > 0
         THEN (busy_gCo2eq + idle_gCo2eq)/(busy_kwh + idle_kwh)
    END
  ) AS avg_intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_project p ON p.project_id = f.project_id
WHERE f.scope='project'
GROUP BY p.cloud_project_name;

CREATE VIEW v_machine_averages AS
SELECT
  m.machine_name,
  AVG(busy_kwh)    AS avg_busy_energy_kwh,
  AVG(idle_kwh)    AS avg_idle_energy_kwh,
  AVG(busy_gCo2eq) AS avg_busy_carbon_gCo2eq,
  AVG(idle_gCo2eq) AS avg_idle_carbon_gCo2eq,
  AVG(
    CASE WHEN (busy_kwh + idle_kwh) > 0
         THEN (busy_gCo2eq + idle_gCo2eq)/(busy_kwh + idle_kwh)
    END
  ) AS avg_intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_machine m ON m.machine_id = f.machine_id
WHERE f.scope='machine'
GROUP BY m.machine_name;

CREATE VIEW v_group_averages AS
SELECT
  g.group_name,
  AVG(f.busy_kwh)    AS avg_busy_energy_kwh,
  AVG(f.idle_kwh)    AS avg_idle_energy_kwh,
  AVG(f.busy_gCo2eq) AS avg_busy_carbon_gCo2eq,
  AVG(f.idle_gCo2eq) AS avg_idle_carbon_gCo2eq,
  AVG(
    CASE WHEN (f.busy_kwh + f.idle_kwh) > 0
         THEN (f.busy_gCo2eq + f.idle_gCo2eq)/(f.busy_kwh + f.idle_kwh)
    END
  ) AS avg_intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_user u ON u.user_id = f.user_id
JOIN dim_group g ON g.group_id = u.group_id
WHERE f.scope='user'
GROUP BY g.group_name;

CREATE VIEW v_user_averages AS
SELECT
  u.user_id,
  AVG(busy_kwh)    AS avg_busy_energy_kwh,
  AVG(idle_kwh)    AS avg_idle_energy_kwh,
  AVG(busy_gCo2eq) AS avg_busy_carbon_gCo2eq,
  AVG(idle_gCo2eq) AS avg_idle_carbon_gCo2eq,
  AVG(
    CASE WHEN (busy_kwh + idle_kwh) > 0
         THEN (busy_gCo2eq + idle_gCo2eq)/(busy_kwh + idle_kwh)
    END
  ) AS avg_intensity_gCo2eq_kwh
FROM fact_usage f
JOIN dim_user u ON u.user_id = f.user_id
WHERE f.scope='user'
GROUP BY u.user_id;
```

## Entity Relationship Diagram
```mermaid
erDiagram
  %% === Dimension tables ===
  dim_group {
    int    group_id PK
    string group_name
  }

  dim_user {
    string user_id PK
    string display_name
    int    group_id FK
  }

  dim_project {
    int    project_id PK
    string cloud_project_name
  }

  dim_machine {
    int    machine_id PK
    string machine_name
  }

  dim_instance {
    int    instance_id PK
    string host
    int    port
    string raw_label
  }

  %% === Mapping tables (M:N helpers) ===
  map_user_project {
    string user_id PK FK
    int    project_id PK FK
  }

  map_project_machine {
    int    project_id PK FK
    int    machine_id PK FK
  }

  %% === Fact tables ===
  fact_usage {
    int    usage_id PK
    string ts
    string scope
    int    project_id FK
    int    machine_id FK
    string user_id   FK
    float  busy_cpu_seconds_total
    float  idle_cpu_seconds_total
    float  busy_kwh
    float  idle_kwh
    float  busy_gCo2eq
    float  idle_gCo2eq
    float  intensity_gCo2eq_kwh
  }

  active_workspace {
    int    workspace_id PK
    int    instance_id  FK
    int    machine_id   FK
    string user_id      FK
    int    project_id   FK
    string started_at
  }

  %% === Relationships ===
  dim_group   ||--o{ dim_user            : has_users
  dim_user    ||--o{ map_user_project    : maps
  dim_project ||--o{ map_user_project    : maps
  dim_project ||--o{ map_project_machine : maps
  dim_machine ||--o{ map_project_machine : maps

  dim_project ||--o{ fact_usage          : project_scope_rows
  dim_machine ||--o{ fact_usage          : machine_scope_rows
  dim_user    ||--o{ fact_usage          : user_scope_rows

  dim_instance||--o{ active_workspace    : hosts
  dim_machine ||--o{ active_workspace    : runs_on
  dim_user    ||--o{ active_workspace    : opened_by
  dim_project ||--o{ active_workspace    : belongs_to

```

## Dependency Diagram
```mermaid
classDiagram
  class fact_usage
  class dim_project
  class dim_machine
  class dim_user
  class dim_group

  class v_ada_timeseries
  class v_project_timeseries
  class v_machine_timeseries
  class v_user_timeseries

  class v_project_totals
  class v_machine_totals
  class v_group_totals
  class v_user_totals

  class v_project_averages
  class v_machine_averages
  class v_group_averages
  class v_user_averages

  v_ada_timeseries     --> fact_usage
  v_project_timeseries --> fact_usage
  v_project_timeseries --> dim_project
  v_machine_timeseries --> fact_usage
  v_machine_timeseries --> dim_machine
  v_user_timeseries    --> fact_usage
  v_user_timeseries    --> dim_user

  v_project_totals     --> fact_usage
  v_project_totals     --> dim_project
  v_machine_totals     --> fact_usage
  v_machine_totals     --> dim_machine
  v_group_totals       --> fact_usage
  v_group_totals       --> dim_user
  v_group_totals       --> dim_group
  v_user_totals        --> fact_usage
  v_user_totals        --> dim_user

  v_project_averages   --> fact_usage
  v_project_averages   --> dim_project
  v_machine_averages   --> fact_usage
  v_machine_averages   --> dim_machine
  v_group_averages     --> fact_usage
  v_group_averages     --> dim_user
  v_group_averages     --> dim_group
  v_user_averages      --> fact_usage
  v_user_averages      --> dim_user
```

# Database Classes
## Prometheus Request Class
We have a Prometheus request class that handles requests to the Prometheus API. This class is used to download cpu_seconds data for a given time period.
## MongoDB Request Class
We have a MongoDB request class that handles requests to the MongoDB database. This class is used to store and retrieve estimated usage data.
## Carbon Intensity API Request Class
We have a Carbon Intensity API request class that handles requests to the Carbon Intensity API. This class is used to get the carbon intensity for a given time period.
## SQLite Class
We have a SQLite class that handles requests to the SQLite database. This class is used to store and retrieve machine averages data.

# Estimating Usage
We estimate usage by downloading cpu_seconds data from Prometheus. We then use machine averages to estimate energy usage and carbon footprint.

The purpose of this project is to provide the users of Ada with information that may lead them towards making greener choices in the future. 
We want users to know what impact they're having on the environment and what they can do reduce their impact.

To achieve this, there are three main variables that we need to make the user aware of.
These are:
* Electricity Usage
* Carbon Intensity
* Carbon Footprint

If users are aware of how their actions affect these three variables, they will be armed with the information necessary
to make the greenes choicest possible. They will be able to minimise their carbon footprint



## Electricity
We estimate electricity usage using machine averages. We multiply the cpu_seconds by the average power consumption of the machine (kW).
## Carbon Intensity
We get the carbon intensity from the Carbon Intensity API. This gives us the carbon intensity (gCo2eq per kwh) for a given time period.
## Carbon Footprint
We estimate carbon footprint using the Carbon Intensity API. We multiply the estimated kwh by the carbon intensity (gCo2eq per kwh).
# Workspace Tracking
We track workspaces by polling Prometheus for active hosts. We estimate their energy usage and carbon footprint using a power model and the Carbon Intensity API.
# Machine Averages
We store machine averages in a SQLite database. We use these averages to estimate energy usage and carbon footprint.
# Group Attribution
We attribute usage to groups based on the cloud_project_name. We store usage data for each group in a MongoDB database.
# User Attribution
We attribute usage to users based on the user label in Prometheus. We store usage data for each user in a MongoDB database.


# Data acquisition breakdown
We store:
* idle_cpu_seconds
* busy_cpu_seconds
* idle_kwh
* busy_kwh
* idle_gCo2eq
* busy_gCo2eq

We store data in a timeseries format for the last year. Data is stored in JSON files.

We store this data for each:
* Project
* Experiment
* Machine
* User

First, we download cpu_seconds data day by day. We make a request for an hours worth of cpu_seconds data.
This gives us a JSON object with a number of timeseries. We parse this object and save its data to various storage classes.
We have a usage storage class for each level of storage mentioned before. If the download fails, we store "failed" instead of a float.



We seperate data into hourly, monthly and yearly so that we can easily load this data to our graphs.

# EstimatedUsageDayEntry
```json
{
  "cloud_project_name": "project",
  "date": "DD_MM_YYYY",
  "timeseries": {
    "totals": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
      "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    },
    "00:00": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
        "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    }
  }
}
```

## MachineMetrics
```json
{
  "machine_name": "Artemis Matlab",
  "metrics": {
    "energy_kwh": {
      "busy": {
        "average": 0.0
      },
      "idle": {
        "average": 0.0
      }
    },
    "carbon_gCo2eq": {
        "busy": {
            "average": 0.0
        },
        "idle": {
            "average": 0.0
      }
    }
  }
}
```

# ActiveWorkspace

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


# workspace tracking
# Workspace System — Quick Guide

This note explains how the **workspace** metrics are collected, stored, and displayed for each site (**clf**, **isis**, **diamond**).

---

## What it does

* Every minute, a poller (`sync_workspaces` management command) queries **Prometheus** to:

  * Find **active hosts** (`up == 1`) for the site.
  * Get **start time** from `node_boot_time_seconds` (used as the workspace’s `started_at`).
  * Compute **idle fraction** from CPU: `rate(node_cpu_seconds_total{mode="idle"}[1m]) / rate(node_cpu_seconds_total[1m])`.
  * Estimate **cores** and **memory activity** (Active / MemTotal).
* At the same time, it fetches current **carbon intensity** (gCO₂/kWh) from the **GB Carbon Intensity API**.
* It estimates per‑minute **energy** for each host, splits it into **busy vs idle**, converts to **kgCO₂e**, and stores everything in the `Workspace` row.

## Where the data shows up

* The **Analysis** page (`/analysis/<site>/`) reads from the `Workspace` table and renders the existing cards.
* Each card shows totals (kWh, kgCO₂e) and a live **Idle Use** ticker based on stored idle energy.

## How the numbers are calculated (per host)

* **Idle fraction** = idle CPU time ÷ total CPU time over the last minute.
* **Power model (W)** per minute:

  * `CPU = cores × cpu_tdp_w × (1 − idle_fraction)`
  * `RAM = ram_w × mem_active_ratio`
  * `Other = other_w`
  * `Watts = CPU + RAM + Other`
* **Energy (kWh)** per minute: `Watts / 1000 × (60 / 3600)`
* **Split**: `busy_kWh = kWh × (1 − idle_fraction)`; `idle_kWh = kWh × idle_fraction`
* **Emissions (kgCO₂e)**: `kWh × (CI_g_per_kWh / 1000)`
* **Runtime seconds** only increases with the **busy** portion.

## How to run

1. Ensure `PROMETHEUS_URL` is set in Django settings.
2. Start the poller (looping):

   ```bash
   python manage.py sync_workspaces --sleep 60
   ```

   Or run one cycle:

   ```bash
   python manage.py sync_workspaces --once
   ```
3. Start the web app:

   ```bash
   python manage.py runserver
   ```
4. Open: `/analysis/clf/`, `/analysis/isis/`, `/analysis/diamond/`.

## Configuration knobs (in the command)

* **Site mapping** → Prom label: `clf/isis/diamond → cloud_project_name` values.
* **Power model**: `cpu_tdp_w`, `ram_w`, `other_w` 
* **Carbon intensity**: fetched live (cached \~5 minutes); fallback used if API is down.




