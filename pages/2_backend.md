---
title: Backend
nav_order: 4    
nav_exclude: false     
---

# Database Structure
## SQL Tables and Views
''' sql
-- ========== DIMENSIONS ==========
CREATE TABLE dim_project (
  project_id        BIGSERIAL PRIMARY KEY,
  cloud_project_name TEXT UNIQUE NOT NULL
);

CREATE TABLE dim_group (
  group_id   BIGSERIAL PRIMARY KEY,
  group_name TEXT UNIQUE NOT NULL
);

CREATE TABLE dim_user (
  user_id    BIGSERIAL PRIMARY KEY,
  ext_user_id TEXT UNIQUE,         -- if you have an external/user-facing ID
  display_name TEXT
);

CREATE TABLE dim_instance (
  instance_id BIGSERIAL PRIMARY KEY,
  hostname    TEXT UNIQUE NOT NULL,    -- e.g. host-172-16-100-116.nubes.stfc.ac.uk:9100
  labels      JSONB DEFAULT '{}'       -- optional Prometheus-like labels
);

CREATE TABLE dim_machine (
  machine_id   BIGSERIAL PRIMARY KEY,
  machine_name TEXT UNIQUE NOT NULL,   -- e.g. 'Artemis (Matlab)'
  instance_id  BIGINT REFERENCES dim_instance(instance_id) ON DELETE SET NULL,
  -- any other hardware fields (cpu model, watts_at_idle, etc.)
  attributes   JSONB DEFAULT '{}'
);

-- Optional relationship helpers if needed
CREATE TABLE bridge_project_group (
  project_id BIGINT REFERENCES dim_project(project_id) ON DELETE CASCADE,
  group_id   BIGINT REFERENCES dim_group(group_id) ON DELETE CASCADE,
  PRIMARY KEY (project_id, group_id)
);

CREATE TABLE bridge_project_user (
  project_id BIGINT REFERENCES dim_project(project_id) ON DELETE CASCADE,
  user_id    BIGINT REFERENCES dim_user(user_id) ON DELETE CASCADE,
  PRIMARY KEY (project_id, user_id)
);

-- ========== WORKSPACE SESSIONS (from "Active workspaces") ==========
CREATE TABLE workspace_session (
  workspace_session_id BIGSERIAL PRIMARY KEY,
  user_id     BIGINT REFERENCES dim_user(user_id) ON DELETE SET NULL,
  machine_id  BIGINT REFERENCES dim_machine(machine_id) ON DELETE SET NULL,
  project_id  BIGINT REFERENCES dim_project(project_id) ON DELETE SET NULL,
  group_id    BIGINT REFERENCES dim_group(group_id) ON DELETE SET NULL,
  started_at  TIMESTAMPTZ NOT NULL,
  ended_at    TIMESTAMPTZ,                 -- NULL => still active
  -- real-time counters if you want to buffer before rolling into facts
  busy_kwh    DOUBLE PRECISION DEFAULT 0,
  idle_kwh    DOUBLE PRECISION DEFAULT 0,
  busy_gco2eq DOUBLE PRECISION DEFAULT 0,
  idle_gco2eq DOUBLE PRECISION DEFAULT 0
);

CREATE INDEX idx_workspace_active ON workspace_session (ended_at) WHERE ended_at IS NULL;

-- ========== FACT TABLES (timeseries) ==========
-- Common metric set: *_cpu_seconds_total, *_kwh, *_gco2eq + intensity
-- Composite PK: (scope_id, timestamp_utc)

-- Ada (global) timeseries
CREATE TABLE fact_usage_ada (
  timestamp_utc           TIMESTAMPTZ NOT NULL,
  busy_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  idle_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  busy_kwh                DOUBLE PRECISION NOT NULL,
  idle_kwh                DOUBLE PRECISION NOT NULL,
  busy_gco2eq             DOUBLE PRECISION NOT NULL,
  idle_gco2eq             DOUBLE PRECISION NOT NULL,
  intensity_gco2eq_per_kwh DOUBLE PRECISION,     -- nullable if not known at ingestion
  PRIMARY KEY (timestamp_utc)
);
CREATE INDEX idx_fact_ada_ts ON fact_usage_ada (timestamp_utc DESC);

-- Project timeseries
CREATE TABLE fact_usage_project (
  project_id              BIGINT NOT NULL REFERENCES dim_project(project_id) ON DELETE CASCADE,
  timestamp_utc           TIMESTAMPTZ NOT NULL,
  busy_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  idle_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  busy_kwh                DOUBLE PRECISION NOT NULL,
  idle_kwh                DOUBLE PRECISION NOT NULL,
  busy_gco2eq             DOUBLE PRECISION NOT NULL,
  idle_gco2eq             DOUBLE PRECISION NOT NULL,
  intensity_gco2eq_per_kwh DOUBLE PRECISION,
  PRIMARY KEY (project_id, timestamp_utc)
);
CREATE INDEX idx_fact_project_ts ON fact_usage_project (timestamp_utc DESC);

-- Machine timeseries
CREATE TABLE fact_usage_machine (
  machine_id              BIGINT NOT NULL REFERENCES dim_machine(machine_id) ON DELETE CASCADE,
  timestamp_utc           TIMESTAMPTZ NOT NULL,
  busy_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  idle_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  busy_kwh                DOUBLE PRECISION NOT NULL,
  idle_kwh                DOUBLE PRECISION NOT NULL,
  busy_gco2eq             DOUBLE PRECISION NOT NULL,
  idle_gco2eq             DOUBLE PRECISION NOT NULL,
  intensity_gco2eq_per_kwh DOUBLE PRECISION,
  PRIMARY KEY (machine_id, timestamp_utc)
);
CREATE INDEX idx_fact_machine_ts ON fact_usage_machine (timestamp_utc DESC);

-- User timeseries
CREATE TABLE fact_usage_user (
  user_id                 BIGINT NOT NULL REFERENCES dim_user(user_id) ON DELETE CASCADE,
  timestamp_utc           TIMESTAMPTZ NOT NULL,
  busy_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  idle_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  busy_kwh                DOUBLE PRECISION NOT NULL,
  idle_kwh                DOUBLE PRECISION NOT NULL,
  busy_gco2eq             DOUBLE PRECISION NOT NULL,
  idle_gco2eq             DOUBLE PRECISION NOT NULL,
  intensity_gco2eq_per_kwh DOUBLE PRECISION,
  PRIMARY KEY (user_id, timestamp_utc)
);
CREATE INDEX idx_fact_user_ts ON fact_usage_user (timestamp_utc DESC);

-- Group timeseries
CREATE TABLE fact_usage_group (
  group_id                BIGINT NOT NULL REFERENCES dim_group(group_id) ON DELETE CASCADE,
  timestamp_utc           TIMESTAMPTZ NOT NULL,
  busy_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  idle_cpu_seconds_total  DOUBLE PRECISION NOT NULL,
  busy_kwh                DOUBLE PRECISION NOT NULL,
  idle_kwh                DOUBLE PRECISION NOT NULL,
  busy_gco2eq             DOUBLE PRECISION NOT NULL,
  idle_gco2eq             DOUBLE PRECISION NOT NULL,
  intensity_gco2eq_per_kwh DOUBLE PRECISION,
  PRIMARY KEY (group_id, timestamp_utc)
);
CREATE INDEX idx_fact_group_ts ON fact_usage_group (timestamp_utc DESC);

-- ========== TOTALS & AVERAGES AS VIEWS ==========
-- You can parameterize by a time window in queries; these views show "lifetime".

-- Project Total (matches your “Project Total”)
CREATE VIEW v_project_total AS
SELECT
  p.project_id,
  p.cloud_project_name,
  SUM(f.busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(f.idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(f.busy_kwh)               AS busy_kwh,
  SUM(f.idle_kwh)               AS idle_kwh,
  SUM(f.busy_gco2eq)            AS busy_gco2eq,
  SUM(f.idle_gco2eq)            AS idle_gco2eq
FROM dim_project p
JOIN fact_usage_project f USING (project_id)
GROUP BY p.project_id, p.cloud_project_name;

-- Machine Total
CREATE VIEW v_machine_total AS
SELECT
  m.machine_id,
  m.machine_name,
  SUM(f.busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(f.idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(f.busy_kwh)               AS busy_kwh,
  SUM(f.idle_kwh)               AS idle_kwh,
  SUM(f.busy_gco2eq)            AS busy_gco2eq,
  SUM(f.idle_gco2eq)            AS idle_gco2eq
FROM dim_machine m
JOIN fact_usage_machine f USING (machine_id)
GROUP BY m.machine_id, m.machine_name;

-- Group Total
CREATE VIEW v_group_total AS
SELECT
  g.group_id,
  g.group_name,
  SUM(f.busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(f.idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(f.busy_kwh)               AS busy_kwh,
  SUM(f.idle_kwh)               AS idle_kwh,
  SUM(f.busy_gco2eq)            AS busy_gco2eq,
  SUM(f.idle_gco2eq)            AS idle_gco2eq
FROM dim_group g
JOIN fact_usage_group f USING (group_id)
GROUP BY g.group_id, g.group_name;

-- User Total
CREATE VIEW v_user_total AS
SELECT
  u.user_id,
  COALESCE(u.display_name, u.ext_user_id) AS user_name,
  SUM(f.busy_cpu_seconds_total) AS busy_cpu_seconds_total,
  SUM(f.idle_cpu_seconds_total) AS idle_cpu_seconds_total,
  SUM(f.busy_kwh)               AS busy_kwh,
  SUM(f.idle_kwh)               AS idle_kwh,
  SUM(f.busy_gco2eq)            AS busy_gco2eq,
  SUM(f.idle_gco2eq)            AS idle_gco2eq
FROM dim_user u
JOIN fact_usage_user f USING (user_id)
GROUP BY u.user_id, COALESCE(u.display_name, u.ext_user_id);

-- “Averages” (mirrors your JSON structure). Example: Project Averages (lifetime).
-- Swap AVG(...) for time-windowed averages in queries as needed.
CREATE VIEW v_project_averages AS
SELECT
  p.project_id,
  p.cloud_project_name,
  AVG(f.busy_kwh)               AS energy_kwh_busy_avg,
  AVG(f.idle_kwh)               AS energy_kwh_idle_avg,
  AVG(f.busy_gco2eq)            AS carbon_gco2eq_busy_avg,
  AVG(f.idle_gco2eq)            AS carbon_gco2eq_idle_avg,
  AVG(f.intensity_gco2eq_per_kwh) AS intensity_gco2eq_per_kwh_avg
FROM dim_project p
JOIN fact_usage_project f USING (project_id)
GROUP BY p.project_id, p.cloud_project_name;

CREATE VIEW v_machine_averages AS
SELECT
  m.machine_id,
  m.machine_name,
  AVG(f.busy_kwh)               AS energy_kwh_busy_avg,
  AVG(f.idle_kwh)               AS energy_kwh_idle_avg,
  AVG(f.busy_gco2eq)            AS carbon_gco2eq_busy_avg,
  AVG(f.idle_gco2eq)            AS carbon_gco2eq_idle_avg,
  AVG(f.intensity_gco2eq_per_kwh) AS intensity_gco2eq_per_kwh_avg
FROM dim_machine m
JOIN fact_usage_machine f USING (machine_id)
GROUP BY m.machine_id, m.machine_name;

CREATE VIEW v_group_averages AS
SELECT
  g.group_id,
  g.group_name,
  AVG(f.busy_kwh)               AS energy_kwh_busy_avg,
  AVG(f.idle_kwh)               AS energy_kwh_idle_avg,
  AVG(f.busy_gco2eq)            AS carbon_gco2eq_busy_avg,
  AVG(f.idle_gco2eq)            AS carbon_gco2eq_idle_avg,
  AVG(f.intensity_gco2eq_per_kwh) AS intensity_gco2eq_per_kwh_avg
FROM dim_group g
JOIN fact_usage_group f USING (group_id)
GROUP BY g.group_id, g.group_name;

CREATE VIEW v_user_averages AS
SELECT
  u.user_id,
  COALESCE(u.display_name, u.ext_user_id) AS user_name,
  AVG(f.busy_kwh)               AS energy_kwh_busy_avg,
  AVG(f.idle_kwh)               AS energy_kwh_idle_avg,
  AVG(f.busy_gco2eq)            AS carbon_gco2eq_busy_avg,
  AVG(f.idle_gco2eq)            AS carbon_gco2eq_idle_avg,
  AVG(f.intensity_gco2eq_per_kwh) AS intensity_gco2eq_per_kwh_avg
FROM dim_user u
JOIN fact_usage_user f USING (user_id)
GROUP BY u.user_id, COALESCE(u.display_name, u.ext_user_id);

'''
## Entity Relationship Diagram
''' mermaid
erDiagram
  dim_project {
    BIGSERIAL project_id PK
    TEXT cloud_project_name
  }

  dim_group {
    BIGSERIAL group_id PK
    TEXT group_name
  }

  dim_user {
    BIGSERIAL user_id PK
    TEXT ext_user_id
    TEXT display_name
  }

  dim_instance {
    BIGSERIAL instance_id PK
    TEXT hostname
    JSONB labels
  }

  dim_machine {
    BIGSERIAL machine_id PK
    TEXT machine_name
    BIGINT instance_id FK
    JSONB attributes
  }

  bridge_project_group {
    BIGINT project_id FK
    BIGINT group_id FK
  }

  bridge_project_user {
    BIGINT project_id FK
    BIGINT user_id FK
  }

  workspace_session {
    BIGSERIAL workspace_session_id PK
    BIGINT user_id FK
    BIGINT machine_id FK
    BIGINT project_id FK
    BIGINT group_id FK
    TIMESTAMPTZ started_at
    TIMESTAMPTZ ended_at
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
  }

  fact_usage_ada {
    TIMESTAMPTZ timestamp_utc PK
    DOUBLE busy_cpu_seconds_total
    DOUBLE idle_cpu_seconds_total
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
    DOUBLE intensity_gco2eq_per_kwh
  }

  fact_usage_project {
    BIGINT project_id PK, FK
    TIMESTAMPTZ timestamp_utc PK
    DOUBLE busy_cpu_seconds_total
    DOUBLE idle_cpu_seconds_total
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
    DOUBLE intensity_gco2eq_per_kwh
  }

  fact_usage_machine {
    BIGINT machine_id PK, FK
    TIMESTAMPTZ timestamp_utc PK
    DOUBLE busy_cpu_seconds_total
    DOUBLE idle_cpu_seconds_total
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
    DOUBLE intensity_gco2eq_per_kwh
  }

  fact_usage_user {
    BIGINT user_id PK, FK
    TIMESTAMPTZ timestamp_utc PK
    DOUBLE busy_cpu_seconds_total
    DOUBLE idle_cpu_seconds_total
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
    DOUBLE intensity_gco2eq_per_kwh
  }

  fact_usage_group {
    BIGINT group_id PK, FK
    TIMESTAMPTZ timestamp_utc PK
    DOUBLE busy_cpu_seconds_total
    DOUBLE idle_cpu_seconds_total
    DOUBLE busy_kwh
    DOUBLE idle_kwh
    DOUBLE busy_gco2eq
    DOUBLE idle_gco2eq
    DOUBLE intensity_gco2eq_per_kwh
  }

  %% Relationships
  dim_instance ||--o{ dim_machine : "hosts"
  dim_machine  ||--o{ workspace_session : "used by"
  dim_user     ||--o{ workspace_session : "starts"
  dim_project  ||--o{ workspace_session : "context"
  dim_group    ||--o{ workspace_session : "context"

  dim_project  ||--o{ fact_usage_project : "has"
  dim_machine  ||--o{ fact_usage_machine : "has"
  dim_user     ||--o{ fact_usage_user    : "has"
  dim_group    ||--o{ fact_usage_group   : "has"

  dim_project  ||--o{ bridge_project_group : "linked to"
  dim_group    ||--o{ bridge_project_group : "linked from"

  dim_project  ||--o{ bridge_project_user : "linked to"
  dim_user     ||--o{ bridge_project_user : "linked from"
'''

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




