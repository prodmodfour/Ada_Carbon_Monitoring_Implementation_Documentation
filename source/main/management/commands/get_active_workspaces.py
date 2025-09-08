import os
import uuid
import json
import math
import time
import sqlite3
import datetime as dt

import pandas as pd
import requests

# -----------------------------
# Config / constants
# -----------------------------
PARQUET_PATH = "node_cpu_seconds_total.parquet"
SQLITE_PATH  = "workspace_metrics.sqlite"
TABLE_NAME   = "workspaces"

# Map Prometheus project label -> Workspace.source
PROJECT_MAP = {
    "CDAaaS": "clf",
    "IDAaaS": "isis",
    "DDAaaS": "diamond",
}
PROJECT_FILTER = set(PROJECT_MAP.keys())

# Power consumption constants (Watts per core) — consistent with project scripts
BUSY_WATTAGE = 12
IDLE_WATTAGE = 1

# Carbon Intensity API (national latest)
CARBON_API_URL = "https://api.carbonintensity.org.uk/intensity"

# Prometheus setup: import from Django settings if available, else env var fallback
PROMETHEUS_URL = None
try:
    import ada_project.settings as settings  # type: ignore
    PROMETHEUS_URL = settings.PROMETHEUS_URL
except Exception:
    PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL")

if not PROMETHEUS_URL:
    print("ERROR: PROMETHEUS_URL not set (Django settings or env var).")
    raise SystemExit(1)

# -----------------------------
# Load parquet and find active hosts
# -----------------------------
if not os.path.exists(PARQUET_PATH):
    print(f"ERROR: '{PARQUET_PATH}' not found. Run the database build first.")
    raise SystemExit(1)

print(f"Loading {PARQUET_PATH} ...")
df = pd.read_parquet(PARQUET_PATH)

# Basic column sanity
required_cols = {"timestamp", "value", "cloud_project_name", "mode"}
missing = required_cols - set(df.columns)
if missing:
    print(f"ERROR: parquet missing required columns: {missing}")
    raise SystemExit(1)

# Pick a hostname label: prefer 'instance', fall back to 'hostname' if present
HOST_LABEL = "instance" if "instance" in df.columns else ("hostname" if "hostname" in df.columns else None)
if HOST_LABEL is None:
    print("ERROR: No 'instance' or 'hostname' label present in parquet.")
    raise SystemExit(1)

# Ensure timestamps are timezone-naive UTC-like (build_database wrote naive)
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

# Latest timestamp present
last_ts = df["timestamp"].max()
print(f"Latest timestamp in parquet: {last_ts}")

# Active hosts = hosts appearing at the last timestamp with desired projects
active_slice = df[(df["timestamp"] == last_ts) & (df["cloud_project_name"].isin(PROJECT_FILTER))]
if active_slice.empty:
    print("No active hosts found at the latest timestamp for target projects.")
    # Still create DB/table so pipeline doesn’t break later
    active_hosts = []
else:
    active_hosts = (
        active_slice[[HOST_LABEL, "cloud_project_name"]]
        .dropna()
        .drop_duplicates()
        .to_dict(orient="records")
    )

print(f"Found {len(active_hosts)} active host(s).")

# -----------------------------
# Prepare SQLite
# -----------------------------
conn = sqlite3.connect(SQLITE_PATH)
cur  = conn.cursor()

cur.execute(f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id TEXT PRIMARY KEY,
    source TEXT,
    instrument TEXT,
    title TEXT,
    owner TEXT,
    hostname TEXT UNIQUE,
    started_at TEXT,

    runtime_seconds INTEGER,
    total_kwh REAL,
    total_kg REAL,

    idle_kwh REAL,
    idle_kg REAL,

    avg_ci_g_per_kwh REAL,
    last_ci_g_per_kwh REAL,
    last_sampled_at TEXT,

    created_at TEXT,
    updated_at TEXT
);
""")
conn.commit()

# -----------------------------
# Fetch current carbon intensity
# -----------------------------
ci_g_per_kwh = None
try:
    r = requests.get(CARBON_API_URL, timeout=15)
    r.raise_for_status()
    payload = r.json()
    # Structure: {"data":[{"intensity":{"forecast":..., "actual":...}, "from":..., "to":...}]}
    data = payload.get("data", [])
    if data:
        intensity = data[0].get("intensity", {}) if isinstance(data[0], dict) else {}
        ci_g_per_kwh = intensity.get("actual", intensity.get("forecast"))
        if ci_g_per_kwh is not None:
            ci_g_per_kwh = float(ci_g_per_kwh)
except Exception as e:
    print(f"WARNING: Failed to fetch carbon intensity: {e}")

now_utc = dt.datetime.utcnow().replace(tzinfo=None)
now_iso = now_utc.isoformat(timespec="seconds") + "Z"

# -----------------------------
# Helper: Prometheus boot time per host
# -----------------------------
# We keep it inline to honor the 'no functions' request.
boot_times = {}
for entry in active_hosts:
    host = entry[HOST_LABEL]
    try:
        # instant vector query
        q = f'node_boot_time_seconds{{{HOST_LABEL}="{host}"}}'
        url = f"{PROMETHEUS_URL}/api/v1/query"
        resp = requests.get(url, params={"query": q}, timeout=20)
        resp.raise_for_status()
        res = resp.json()
        result = res.get("data", {}).get("result", [])
        if not result:
            print(f"WARNING: No boot time for host {host}; skipping.")
            continue
        # value format: [ <unix_ts>, "<value>" ]
        val = result[0].get("value", [])
        if len(val) != 2:
            print(f"WARNING: Unexpected boot time format for {host}; skipping.")
            continue
        boot_epoch = float(val[1])
        # Convert to naive UTC datetime to match parquet
        boot_dt = dt.datetime.utcfromtimestamp(boot_epoch)
        boot_times[host] = boot_dt
    except Exception as e:
        print(f"WARNING: Failed to fetch boot time for {host}: {e}")

# -----------------------------
# Aggregate since boot, compute energy + carbon, persist
# -----------------------------
for entry in active_hosts:
    host = entry[HOST_LABEL]
    project = entry["cloud_project_name"]

    if host not in boot_times:
        # Skip hosts we couldn't resolve boot time for
        continue

    started_at = boot_times[host]

    # Slice this host since boot (inclusive)
    host_df = df[(df[HOST_LABEL] == host) & (df["timestamp"] >= started_at)]
    if host_df.empty:
        print(f"WARNING: No samples since boot for {host}; skipping.")
        continue

    # Tally idle / busy seconds across all cores
    idle_seconds = host_df.loc[host_df["mode"] == "idle", "value"].sum()
    busy_seconds = host_df.loc[host_df["mode"] != "idle", "value"].sum()

    # Guard against NaNs
    idle_seconds = float(0.0 if math.isnan(idle_seconds) else idle_seconds)
    busy_seconds = float(0.0 if math.isnan(busy_seconds) else busy_seconds)

    # Energy (Wh), then kWh
    idle_wh = idle_seconds * IDLE_WATTAGE / 3600.0
    busy_wh = busy_seconds * BUSY_WATTAGE / 3600.0

    idle_kwh = idle_wh / 1000.0 if False else idle_wh  # already Wh→kWh above (keep as is)
    busy_kwh = busy_wh

    total_kwh = idle_kwh + busy_kwh

    # Carbon (kgCO2e) if we have CI (g/kWh)
    if ci_g_per_kwh is not None:
        idle_kg  = idle_kwh * ci_g_per_kwh / 1000.0
        total_kg = total_kwh * ci_g_per_kwh / 1000.0
    else:
        idle_kg = 0.0
        total_kg = 0.0

    # Runtime = "active" time -> busy seconds
    runtime_seconds = int(round(busy_seconds))

    # Map project -> source code used by Workspace
    source = PROJECT_MAP.get(project)
    if not source:
        # Shouldn't happen due to filter, but be safe
        continue

    # Upsert by hostname (unique)
    # Generate a stable UUID if row doesn't exist yet
    cur.execute(f"SELECT id FROM {TABLE_NAME} WHERE hostname = ?", (host,))
    row = cur.fetchone()
    if row:
        row_id = row[0]
    else:
        row_id = str(uuid.uuid4())

    # ISO strings
    started_iso = started_at.isoformat(timespec="seconds") + "Z"
    last_sampled_iso = now_iso

    payload = {
        "id": row_id,
        "source": source,
        "instrument": "",
        "title": "Workspace",
        "owner": "",
        "hostname": host,
        "started_at": started_iso,
        "runtime_seconds": runtime_seconds,
        "total_kwh": float(round(total_kwh, 6)),
        "total_kg": float(round(total_kg, 6)),
        "idle_kwh": float(round(idle_kwh, 6)),
        "idle_kg": float(round(idle_kg, 6)),
        "avg_ci_g_per_kwh": float(ci_g_per_kwh) if ci_g_per_kwh is not None else None,
        "last_ci_g_per_kwh": float(ci_g_per_kwh) if ci_g_per_kwh is not None else None,
        "last_sampled_at": last_sampled_iso,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    # REPLACE INTO ensures id uniqueness, and hostname is UNIQUE, so we first ensure the id chosen
    cur.execute(f"""
        INSERT INTO {TABLE_NAME} (
            id, source, instrument, title, owner, hostname, started_at,
            runtime_seconds, total_kwh, total_kg, idle_kwh, idle_kg,
            avg_ci_g_per_kwh, last_ci_g_per_kwh, last_sampled_at,
            created_at, updated_at
        )
        VALUES (
            :id, :source, :instrument, :title, :owner, :hostname, :started_at,
            :runtime_seconds, :total_kwh, :total_kg, :idle_kwh, :idle_kg,
            :avg_ci_g_per_kwh, :last_ci_g_per_kwh, :last_sampled_at,
            :created_at, :updated_at
        )
        ON CONFLICT(hostname) DO UPDATE SET
            source=excluded.source,
            instrument=excluded.instrument,
            title=excluded.title,
            owner=excluded.owner,
            started_at=excluded.started_at,
            runtime_seconds=excluded.runtime_seconds,
            total_kwh=excluded.total_kwh,
            total_kg=excluded.total_kg,
            idle_kwh=excluded.idle_kwh,
            idle_kg=excluded.idle_kg,
            avg_ci_g_per_kwh=excluded.avg_ci_g_per_kwh,
            last_ci_g_per_kwh=excluded.last_ci_g_per_kwh,
            last_sampled_at=excluded.last_sampled_at,
            updated_at=excluded.updated_at
        ;
    """, payload)

    print(f"Saved workspace row for host '{host}' (source={source}).")

conn.commit()
conn.close()

print(f"Done. Wrote workspace metrics to '{SQLITE_PATH}' (table '{TABLE_NAME}').")
