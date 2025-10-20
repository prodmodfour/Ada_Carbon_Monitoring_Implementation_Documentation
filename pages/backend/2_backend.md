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

```python
import requests

class PrometheusAPIClient:
    def __init__(self, prometheus_url = "https://host-172-16-100-248.nubes.stfc.ac.uk/", api_endpoint = "api/v1/query_range", timeout=120):
        if not prometheus_url.endswith("/"):
            prometheus_url = prometheus_url + "/"
        
        if api_endpoint.startswith("/"):
            api_endpoint = api_endpoint[1:]

        self.base_url = prometheus_url
        self.api_endpoint = api_endpoint
        self.url = self.base_url + self.api_endpoint
        self.timeout = timeout

    def query(self, parameters):
        try:
            # Make the request
            response = requests.get(self.url, params=parameters, timeout=self.timeout)

            print("URL:", response.url)
            print("Status:", response.status_code, response.reason)
            response.raise_for_status()  # raises on 4xx/5xx
            print("OK → proceeding to parse JSON")
            data = response.json()
            print("Prometheus status:", data.get("status"))
            return data

        except requests.exceptions.ReadTimeout:
            print(f"Request timed out for entry at {parameters.get("start")}. Skipping.")

            return None
        except requests.HTTPError as e:
            try:
                print("Error body:", response.text)
            except Exception:
                pass
        except Exception:
            pass
            print(f"HTTPError for entry at {parameters.get("start")}. Skipping.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"RequestException for entry at {parameters.get("start")}. Skipping.")
            return None
        return None
```
## MongoDB Request Class
We have a MongoDB request class that handles requests to the MongoDB database. This class is used to read data from the MongoDB

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Union

from pymongo import MongoClient, ReadPreference
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.read_concern import ReadConcern


@dataclass
class MongoReaderConfig:
    """Configuration for MongoReader."""
    uri: str                                # e.g. "mongodb+srv://user:pass@cluster.example.mongodb.net"
    database: str                           # database to use by default
    read_preference: ReadPreference = ReadPreference.SECONDARY_PREFERRED
    read_concern: ReadConcern = ReadConcern("majority")
    app_name: str = "MongoReader"
    socket_timeout_ms: Optional[int] = 10_000
    server_selection_timeout_ms: Optional[int] = 10_000
    max_idle_time_ms: Optional[int] = 60_000
    # Limit per-operation time on the server; can be overridden per call
    default_max_time_ms: Optional[int] = 10_000


class MongoReader:
    """
    A read-only MongoDB client focused on fetching data (no writes).

    Notes on safety:
    - This class only exposes read methods and never calls insert/update/delete APIs.
    - For *true* write protection, use a MongoDB user with read-only roles.
    """

    def __init__(self, config: MongoReaderConfig):
        self._config = config
        # retryWrites=False ensures no accidental write retries (reads don't write, but be explicit)
        self._client = MongoClient(
            config.uri,
            appname=config.app_name,
            read_preference=config.read_preference,
            retryWrites=False,
            socketTimeoutMS=config.socket_timeout_ms,
            serverSelectionTimeoutMS=config.server_selection_timeout_ms,
            maxIdleTimeMS=config.max_idle_time_ms,
        )
        self._db: Database = self._client.get_database(
            config.database, read_concern=config.read_concern
        )

    # --- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MongoReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # --- helpers -----------------------------------------------------------

    def _coll(self, name: str) -> Collection:
        return self._db.get_collection(name)

    # --- read-only operations ---------------------------------------------

    def ping(self) -> bool:
        """Check connectivity."""
        self._client.admin.command("ping")
        return True

    def list_collections(self) -> List[str]:
        """List collection names in the database."""
        return self._db.list_collection_names()

    def find_one(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        max_time_ms: Optional[int] = None,
        sort: Optional[List[tuple]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the first matching document (or None)."""
        kwargs: Dict[str, Any] = {}
        if projection is not None:
            kwargs["projection"] = projection
        if max_time_ms is None:
            max_time_ms = self._config.default_max_time_ms
        if sort is not None:
            kwargs["sort"] = sort
        return self._coll(collection).find_one(
            filter or {}, max_time_ms=max_time_ms, **kwargs
        )

    def find(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        skip: int = 0,
        batch_size: Optional[int] = None,
        max_time_ms: Optional[int] = None,
        allow_disk_use: Optional[bool] = None,
        hint: Optional[Union[str, List[tuple]]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream matching documents as an iterator.
        """
        cursor = self._coll(collection).find(
            filter or {},
            projection=projection,
            skip=skip,
            limit=limit or 0,
            sort=sort,
            batch_size=batch_size or 0,
            max_time_ms=max_time_ms or self._config.default_max_time_ms,
            allow_disk_use=allow_disk_use,
            hint=hint,
        )
        for doc in cursor:
            yield doc

    def aggregate(
        self,
        collection: str,
        pipeline: Sequence[Dict[str, Any]],
        allow_disk_use: Optional[bool] = None,
        max_time_ms: Optional[int] = None,
        hint: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> Iterable[Dict[str, Any]]:
        """
        Run a read-only aggregation pipeline.
        (Avoid $out/$merge stages—they write to collections and are not allowed here.)
        """
        # Quick safeguard: reject pipelines containing $out or $merge
        forbidden = {"$out", "$merge"}
        for stage in pipeline:
            if any(op in forbidden for op in stage):
                raise ValueError("Aggregation stages $out/$merge are not permitted.")
        cursor = self._coll(collection).aggregate(
            list(pipeline),
            allowDiskUse=allow_disk_use,
            maxTimeMS=max_time_ms or self._config.default_max_time_ms,
            hint=hint,
        )
        for doc in cursor:
            yield doc

    def distinct(
        self,
        collection: str,
        key: str,
        filter: Optional[Dict[str, Any]] = None,
        max_time_ms: Optional[int] = None,
    ) -> List[Any]:
        """Get distinct values for a field."""
        return self._coll(collection).distinct(
            key,
            filter or {},
            maxTimeMS=max_time_ms or self._config.default_max_time_ms,
        )

    def count(
        self,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        max_time_ms: Optional[int] = None,
        hint: Optional[Union[str, List[tuple]]] = None,
        *,
        estimated: bool = False,
    ) -> int:
        """
        Count documents.
        - estimated=True uses collection.estimated_document_count() (fast, approximate).
        - estimated=False uses count_documents(filter) (accurate, uses index/scan).
        """
        if estimated and (filter is None or filter == {}):
            return int(self._coll(collection).estimated_document_count())
        return int(
            self._coll(collection).count_documents(
                filter or {},
                maxTimeMS=max_time_ms or self._config.default_max_time_ms,
                hint=hint,
            )
        )

```
## Carbon Intensity API Request Class
We have a Carbon Intensity API request class that handles requests to the Carbon Intensity API. This class is used to get the carbon intensity for a given time period.
```python
import requests
import typing
from datetime import datetime, timedelta

class CarbonIntensityAPIClient:
    def __init__(self):
        self.api_url = "https://api.carbonintensity.org.uk/intensity"

    def get_carbon_intensity(self, start: datetime) -> float | None:
        # Define the end of the first 30-min slot and the end of the hour
        mid_time = start + timedelta(minutes=30)
        end_time = start + timedelta(hours=1)

        # The API expects time in ISO 8601 format (e.g., 2025-09-23T17:00Z)
        # We format the datetime objects into strings for the URL
        start_str = start.strftime('%Y-%m-%dT%H:%MZ')
        mid_str = mid_time.strftime('%Y-%m-%dT%H:%MZ')
        end_str = end_time.strftime('%Y-%m-%dT%H:%MZ')

        # Construct the URLs for the two separate half-hour periods
        url_first_half = f"{self.api_url}/{start_str}/{mid_str}"
        url_second_half = f"{self.api_url}/{mid_str}/{end_str}"

        try:
            # --- Get data for the first half-hour ---
            response1 = requests.get(url_first_half)
            response1.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            data1 = response1.json()
            # The API returns a list of data points; we need the first one.
            intensity1 = data1['data'][0]['intensity']['actual']

            # --- Get data for the second half-hour ---
            response2 = requests.get(url_second_half)
            response2.raise_for_status()
            data2 = response2.json()
            intensity2 = data2['data'][0]['intensity']['actual']

            # --- Calculate and return the average ---
            average_intensity = (intensity1 + intensity2) / 2
            print(f"Average intensity: {average_intensity}")
            return average_intensity


        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return 0
        except (KeyError, IndexError) as e:
            # This can happen if the JSON structure is unexpected or empty
            print(f"Failed to parse data from API response: {e}")
            return 0
```
## SQLite Class
We have a SQLite class that handles requests to the SQLite database. 

```python
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional


# ---- Small utility: dict rows ------------------------------------------------
def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description or [])}


# ---- Main DB class -----------------------------------------------------------
@dataclass
class UsageDB:
    path: str = ":memory:"
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.conn = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        self.conn.row_factory = _dict_factory
        self._configure()
        self.create_all()

    # -- connection/pragma -----------------------------------------------------
    def _configure(self) -> None:
        cur = self.conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
        cur.execute("PRAGMA synchronous = NORMAL;")
        cur.execute("PRAGMA temp_store = MEMORY;")

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    @contextmanager
    def transaction(self):
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN;")
            yield
            cur.execute("COMMIT;")
        except Exception:
            cur.execute("ROLLBACK;")
            raise

    # -- schema ----------------------------------------------------------------
    def create_all(self) -> None:
        cur = self.conn.cursor()
        # Dimension tables
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS dim_group (
          group_id     INTEGER PRIMARY KEY,
          group_name   TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS dim_user (
          user_id      TEXT PRIMARY KEY,
          display_name TEXT,
          group_id     INTEGER REFERENCES dim_group(group_id) ON UPDATE CASCADE ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS dim_project (
          project_id           INTEGER PRIMARY KEY,
          cloud_project_name   TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS dim_machine (
          machine_id   INTEGER PRIMARY KEY,
          machine_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS map_user_project (
          user_id    TEXT    NOT NULL REFERENCES dim_user(user_id)    ON DELETE CASCADE,
          project_id INTEGER NOT NULL REFERENCES dim_project(project_id) ON DELETE CASCADE,
          PRIMARY KEY (user_id, project_id)
        );

        CREATE TABLE IF NOT EXISTS map_project_machine (
          project_id INTEGER NOT NULL REFERENCES dim_project(project_id) ON DELETE CASCADE,
          machine_id INTEGER NOT NULL REFERENCES dim_machine(machine_id) ON DELETE CASCADE,
          PRIMARY KEY (project_id, machine_id)
        );

        CREATE TABLE IF NOT EXISTS dim_instance (
          instance_id INTEGER PRIMARY KEY,
          host        TEXT NOT NULL,
          port        INTEGER,
          raw_label   TEXT
        );
        """)

        # Fact tables
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS fact_usage (
          usage_id     INTEGER PRIMARY KEY,
          ts           TEXT    NOT NULL,
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
          intensity_gCo2eq_kwh   REAL,

          CHECK ( (scope='ada'     AND project_id IS NULL AND machine_id IS NULL AND user_id IS NULL)
               OR (scope='project' AND project_id IS NOT NULL AND machine_id IS NULL AND user_id IS NULL)
               OR (scope='machine' AND machine_id IS NOT NULL AND project_id IS NULL AND user_id IS NULL)
               OR (scope='user'    AND user_id    IS NOT NULL AND project_id IS NULL AND machine_id IS NULL)
          ),

          UNIQUE (scope, ts, COALESCE(project_id, -1), COALESCE(machine_id, -1), COALESCE(user_id, ''))
        );

        CREATE INDEX IF NOT EXISTS idx_fact_usage_ts       ON fact_usage(ts);
        CREATE INDEX IF NOT EXISTS idx_fact_usage_scope    ON fact_usage(scope);
        CREATE INDEX IF NOT EXISTS idx_fact_usage_project  ON fact_usage(project_id) WHERE project_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_fact_usage_machine  ON fact_usage(machine_id) WHERE machine_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_fact_usage_user     ON fact_usage(user_id)    WHERE user_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS active_workspace (
          workspace_id INTEGER PRIMARY KEY,
          instance_id  INTEGER NOT NULL REFERENCES dim_instance(instance_id),
          machine_id   INTEGER NOT NULL REFERENCES dim_machine(machine_id),
          user_id      TEXT REFERENCES dim_user(user_id),
          project_id   INTEGER REFERENCES dim_project(project_id),
          started_at   TEXT  NOT NULL
        );
        """)

        # Views
        cur.executescript("""
        CREATE VIEW IF NOT EXISTS v_ada_timeseries AS
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

        CREATE VIEW IF NOT EXISTS v_project_timeseries AS
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

        CREATE VIEW IF NOT EXISTS v_machine_timeseries AS
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

        CREATE VIEW IF NOT EXISTS v_user_timeseries AS
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

        CREATE VIEW IF NOT EXISTS v_project_totals AS
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

        CREATE VIEW IF NOT EXISTS v_machine_totals AS
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

        CREATE VIEW IF NOT EXISTS v_group_totals AS
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

        CREATE VIEW IF NOT EXISTS v_user_totals AS
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

        CREATE VIEW IF NOT EXISTS v_project_averages AS
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

        CREATE VIEW IF NOT EXISTS v_machine_averages AS
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

        CREATE VIEW IF NOT EXISTS v_group_averages AS
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

        CREATE VIEW IF NOT EXISTS v_user_averages AS
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
        """)

    # -- get-or-create helpers -------------------------------------------------
    def get_or_create_group(self, group_name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO dim_group(group_name) VALUES (?)", (group_name,))
        cur.execute("SELECT group_id FROM dim_group WHERE group_name=?", (group_name,))
        return cur.fetchone()["group_id"]

    def get_or_create_user(self, user_id: str, display_name: Optional[str] = None,
                           group_name: Optional[str] = None) -> str:
        group_id = None
        if group_name:
            group_id = self.get_or_create_group(group_name)
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO dim_user(user_id, display_name, group_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              display_name=COALESCE(excluded.display_name, dim_user.display_name),
              group_id=COALESCE(excluded.group_id, dim_user.group_id)
        """, (user_id, display_name, group_id))
        return user_id

    def get_or_create_project(self, cloud_project_name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO dim_project(cloud_project_name) VALUES (?)", (cloud_project_name,))
        cur.execute("SELECT project_id FROM dim_project WHERE cloud_project_name=?", (cloud_project_name,))
        return cur.fetchone()["project_id"]

    def get_or_create_machine(self, machine_name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO dim_machine(machine_name) VALUES (?)", (machine_name,))
        cur.execute("SELECT machine_id FROM dim_machine WHERE machine_name=?", (machine_name,))
        return cur.fetchone()["machine_id"]

    def get_or_create_instance(self, host: str, port: Optional[int] = None,
                               raw_label: Optional[str] = None) -> int:
        cur = self.conn.cursor()
        # no natural unique key → create if exact tuple not present
        cur.execute("""
            INSERT INTO dim_instance(host, port, raw_label) VALUES (?, ?, ?)
        """, (host, port, raw_label))
        return cur.lastrowid

    # -- mapping helpers -------------------------------------------------------
    def map_user_project(self, user_id: str, project_id: int | None = None,
                         cloud_project_name: str | None = None) -> None:
        if project_id is None:
            if not cloud_project_name:
                raise ValueError("Provide project_id or cloud_project_name")
            project_id = self.get_or_create_project(cloud_project_name)
        self.get_or_create_user(user_id)  # ensure user exists
        self.conn.execute(
            "INSERT OR IGNORE INTO map_user_project(user_id, project_id) VALUES (?, ?)",
            (user_id, project_id)
        )

    def map_project_machine(self, project_id: int | None = None, machine_id: int | None = None,
                            cloud_project_name: str | None = None, machine_name: str | None = None) -> None:
        if project_id is None:
            if not cloud_project_name:
                raise ValueError("Provide project_id or cloud_project_name")
            project_id = self.get_or_create_project(cloud_project_name)
        if machine_id is None:
            if not machine_name:
                raise ValueError("Provide machine_id or machine_name")
            machine_id = self.get_or_create_machine(machine_name)
        self.conn.execute(
            "INSERT OR IGNORE INTO map_project_machine(project_id, machine_id) VALUES (?, ?)",
            (project_id, machine_id)
        )

    # -- active workspaces -----------------------------------------------------
    def start_workspace(self, instance_id: int, machine_id: int,
                        started_at_iso_utc: str, user_id: Optional[str] = None,
                        project_id: Optional[int] = None) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO active_workspace(instance_id, machine_id, user_id, project_id, started_at)
            VALUES (?, ?, ?, ?, ?)
        """, (instance_id, machine_id, user_id, project_id, started_at_iso_utc))
        return cur.lastrowid

    # -- fact_usage inserts ----------------------------------------------------
    @staticmethod
    def _validate_scope(scope: str,
                        project_id: Optional[int],
                        machine_id: Optional[int],
                        user_id: Optional[str]) -> None:
        if scope not in {"ada", "project", "machine", "user"}:
            raise ValueError("scope must be one of {'ada','project','machine','user'}")
        want = {
            "ada":      (None, None, None),
            "project":  ("req", None, None),
            "machine":  (None, "req", None),
            "user":     (None, None, "req"),
        }[scope]
        checks = [
            (want[0], project_id, "project_id"),
            (want[1], machine_id, "machine_id"),
            (want[2], user_id, "user_id"),
        ]
        for expected, provided, name in checks:
            if expected == "req" and provided is None:
                raise ValueError(f"{name} is required for scope='{scope}'")
            if expected is None and provided is not None and scope != name.split("_")[0]:
                # ensure *only* the required key is set
                # (the SQL CHECK also enforces this)
                raise ValueError(f"{name} must be NULL for scope='{scope}'")

    def insert_fact_usage(self, *, scope: str, ts_iso_utc: str,
                          project_id: Optional[int] = None,
                          machine_id: Optional[int] = None,
                          user_id: Optional[str] = None,
                          busy_cpu_seconds_total: float = 0.0,
                          idle_cpu_seconds_total: float = 0.0,
                          busy_kwh: float = 0.0,
                          idle_kwh: float = 0.0,
                          busy_gCo2eq: float = 0.0,
                          idle_gCo2eq: float = 0.0,
                          intensity_gCo2eq_kwh: Optional[float] = None) -> int:
        self._validate_scope(scope, project_id, machine_id, user_id)
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO fact_usage(
              ts, scope, project_id, machine_id, user_id,
              busy_cpu_seconds_total, idle_cpu_seconds_total,
              busy_kwh, idle_kwh, busy_gCo2eq, idle_gCo2eq, intensity_gCo2eq_kwh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope, ts, COALESCE(project_id, -1), COALESCE(machine_id, -1), COALESCE(user_id, ''))
            DO UPDATE SET
              busy_cpu_seconds_total = excluded.busy_cpu_seconds_total,
              idle_cpu_seconds_total = excluded.idle_cpu_seconds_total,
              busy_kwh               = excluded.busy_kwh,
              idle_kwh               = excluded.idle_kwh,
              busy_gCo2eq            = excluded.busy_gCo2eq,
              idle_gCo2eq            = excluded.idle_gCo2eq,
              intensity_gCo2eq_kwh   = excluded.intensity_gCo2eq_kwh
        """, (
            ts_iso_utc, scope, project_id, machine_id, user_id,
            busy_cpu_seconds_total, idle_cpu_seconds_total,
            busy_kwh, idle_kwh, busy_gCo2eq, idle_gCo2eq, intensity_gCo2eq_kwh
        ))
        return cur.lastrowid

    def bulk_insert_fact_usage(self, rows: Iterable[Mapping[str, Any]]) -> None:
        with self.transaction():
            for r in rows:
                self.insert_fact_usage(**r)

    # -- query helpers (views) -------------------------------------------------
    def q(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        return list(self.conn.execute(sql, params))

    # Timeseries
    def ada_timeseries(self) -> list[dict]:
        return self.q("SELECT * FROM v_ada_timeseries ORDER BY ts")

    def project_timeseries(self, cloud_project_name: str) -> list[dict]:
        return self.q("""
            SELECT * FROM v_project_timeseries
            WHERE cloud_project_name=? ORDER BY ts
        """, (cloud_project_name,))

    def machine_timeseries(self, machine_name: str) -> list[dict]:
        return self.q("""
            SELECT * FROM v_machine_timeseries
            WHERE machine_name=? ORDER BY ts
        """, (machine_name,))

    def user_timeseries(self, user_id: str) -> list[dict]:
        return self.q("""
            SELECT * FROM v_user_timeseries
            WHERE user_id=? ORDER BY ts
        """, (user_id,))

    # Totals
    def project_totals(self) -> list[dict]:
        return self.q("SELECT * FROM v_project_totals ORDER BY cloud_project_name")

    def machine_totals(self) -> list[dict]:
        return self.q("SELECT * FROM v_machine_totals ORDER BY machine_name")

    def group_totals(self) -> list[dict]:
        return self.q("SELECT * FROM v_group_totals ORDER BY group_name")

    def user_totals(self) -> list[dict]:
        return self.q("SELECT * FROM v_user_totals ORDER BY user_id")

    # Averages
    def project_averages(self) -> list[dict]:
        return self.q("SELECT * FROM v_project_averages ORDER BY cloud_project_name")

    def machine_averages(self) -> list[dict]:
        return self.q("SELECT * FROM v_machine_averages ORDER BY machine_name")

    def group_averages(self) -> list[dict]:
        return self.q("SELECT * FROM v_group_averages ORDER BY group_name")

    def user_averages(self) -> list[dict]:
        return self.q("SELECT * FROM v_user_averages ORDER BY user_id")
```

# Estimating Usage
We estimate usage by downloading cpu_seconds data from Prometheus. We then use machine averages to estimate energy usage and carbon footprint.



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


