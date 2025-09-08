# generate_fake_node_cpu.py
# Creates: node_cpu_seconds_total.parquet
# One year of hourly records for CDAaaS, IDAaaS, DDAaaS.

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---- configuration (simple, fixed) ----
OUTPUT_FILE = "node_cpu_seconds_total.parquet"
PROJECTS = ["CDAaaS", "IDAaaS", "DDAaaS"]
HOURS = 365 * 24  # one year, hourly
RNG_SEED = 42

# ---- build a UTC hourly timeline covering the last 365 days ----
now_utc = pd.Timestamp.utcnow().floor("H")
start = now_utc - pd.Timedelta(hours=HOURS - 1)
timestamps = pd.date_range(start, periods=HOURS, freq="H", tz="UTC")

# ---- simple synthetic load model ----
# We'll simulate a diurnal cycle plus noise to produce busy vs idle seconds.
rng = np.random.default_rng(RNG_SEED)

rows = []
for proj in PROJECTS:
    # Choose a fixed (but different) "core count" per project to scale seconds
    # (purely for realism; your calculator just sums these numbers).
    cores = rng.integers(8, 33)  # 8–32 cores

    # Per-project baseline utilization makes projects differ a bit
    base_util = rng.uniform(0.25, 0.65)

    # Build hourly utilization with a day-night rhythm
    hours_of_day = np.arange(HOURS) % 24
    diurnal = 0.20 * (1 + np.sin((hours_of_day - 6) / 24 * 2 * np.pi))  # peaks ~midday
    noise = rng.normal(0, 0.07, size=HOURS)

    util = np.clip(base_util + diurnal + noise, 0.02, 0.98)  # clamp 2%..98%

    # Convert utilization into CPU-seconds per hour across all cores
    total_cpu_seconds = cores * 3600.0
    busy_seconds = util * total_cpu_seconds
    idle_seconds = (1.0 - util) * total_cpu_seconds

    # Create two rows per timestamp (idle & busy)
    # Keep values as float64; your script will aggregate them.
    rows.extend(
        zip(
            [proj] * HOURS,
            ["busy"] * HOURS,
            timestamps,
            busy_seconds.astype("float64"),
        )
    )
    rows.extend(
        zip(
            [proj] * HOURS,
            ["idle"] * HOURS,
            timestamps,
            idle_seconds.astype("float64"),
        )
    )

# ---- assemble and write parquet ----
df = pd.DataFrame(rows, columns=["cloud_project_name", "mode", "timestamp", "value"])

# Ensure dtypes your calculator likes
try:
    df = df.astype(
        {
            "cloud_project_name": "string[pyarrow]",
            "mode": "string[pyarrow]",
            "value": "float64",
        }
    )
except Exception:
    df = df.astype(
        {
            "cloud_project_name": "string",
            "mode": "string",
            "value": "float64",
        }
    )

# (timestamp already tz-aware UTC)
table = pa.Table.from_pandas(df, preserve_index=False)
pq.write_table(table, OUTPUT_FILE)

print(
    f"Wrote {len(df):,} rows to {OUTPUT_FILE} "
    f"({len(PROJECTS)} projects × {HOURS} hours × 2 modes)."
)
