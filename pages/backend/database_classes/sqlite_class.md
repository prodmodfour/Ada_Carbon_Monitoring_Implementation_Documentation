---
title: SQLite Class
parent: Database Classes
nav_order: 4
---

# Todo
* Class diagram
* Functionality examples
* Couple to given sql tables


# SQLite Class

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
