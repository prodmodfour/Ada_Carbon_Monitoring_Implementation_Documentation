---
title: SQL Table Recipes
parent: Database Structure
nav_order: 1
---

# SQL Tables and Views

## Dimension Tables 

```sql
CREATE TABLE dim_group (
  group_id     INTEGER PRIMARY KEY,
  group_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_user (
  user_id      TEXT PRIMARY KEY,          
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

CREATE TABLE dim_instance (
  instance_id INTEGER PRIMARY KEY,
  host        TEXT NOT NULL,
  port        INTEGER,
  raw_label   TEXT        
);
```

## Many-to-many helpers
```sql
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
```

## Fact Tables 
* Single flexible timeseries for *all* scopes (Ada, Project, Machine, User)

```sql
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
```
## Active Workspaces Table
```sql
CREATE TABLE active_workspace (
  workspace_id INTEGER PRIMARY KEY,
  instance_id  INTEGER NOT NULL REFERENCES dim_instance(instance_id),
  machine_id   INTEGER NOT NULL REFERENCES dim_machine(machine_id),
  user_id      TEXT REFERENCES dim_user(user_id),
  project_id   INTEGER REFERENCES dim_project(project_id),
  started_at   TEXT  NOT NULL   -- ISO-8601 UTC
  -- Note: per-workspace energy/carbon shouldn’t live here; they belong in fact_usage
);
```

## Derived “Totals” and “Averages” as VIEWS
```sql
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

-- Here “average” is the arithmetic mean across rows in the chosen timeseries.

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
