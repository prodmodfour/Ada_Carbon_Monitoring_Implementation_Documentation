from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
import pyarrow 
import gc

class Command(BaseCommand):
    help = "Calculate project usage and estimate electricity consumption."

    def handle(self, *args, **kwargs):
        print("Starting calculation of project electricity usage.")

        # -- Todo: Move to database settings.py
        INPUT_FILE = "node_cpu_seconds_total.parquet"
        OUTPUT_FILE = "project_estimated_electricity_usage.parquet"
        PROJECT_NAMES = ["CDAaaS", "IDAaaS", "DDAaaS"]

        # Power consumption constants (Watts per core)
        BUSY_WATTAGE = 12
        IDLE_WATTAGE = 1
        needed_cols = ["cloud_project_name", "timestamp", "mode", "value"]
        ## ---------------------------

        

        try:
            print(f"Loading data from '{INPUT_FILE}' (columns={needed_cols})...")
            df = pd.read_parquet(INPUT_FILE, columns=needed_cols)
            if df.empty:
                print("Input parquet is empty; nothing to do.")
                return
            print(f"Loaded {len(df):,} rows")
        except FileNotFoundError:
            print(
                f"Error: Input file '{INPUT_FILE}' not found. "
                "Please run the 'build_database' command first."
            )
            return
        except Exception as e:
            print(f"An error occurred while reading the Parquet file: {e}")
            return

        # Filter to only the projects we care about (early to cut memory)
        df = df[df["cloud_project_name"].isin(PROJECT_NAMES)].copy()
        if df.empty:
            print("No rows matched the requested projects; exiting.")
            return

        # Normalize dtypes to reduce memory footprint
        df["cloud_project_name"] = df["cloud_project_name"].astype("category")
        df["mode"] = df["mode"].astype("category")

        # Ensure timestamp is parsed; if tz-aware, convert to UTC then drop tz (save as UTC-naive)
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        ts_na = ts.dt.tz_convert("UTC").dt.tz_localize(None)
        df["timestamp"] = ts_na

        # value can usually be downcast safely; if very large, keep float64
        if np.issubdtype(df["value"].dtype, np.floating):
            df["value"] = df["value"].astype("float32")

        all_projects = []

        for project in PROJECT_NAMES:
            print(f"Processing project: {project}...")
            proj = df[df["cloud_project_name"] == project][["timestamp", "mode", "value"]]
            if proj.empty:
                print(f"Warning: No data found for project '{project}'. Skipping.")
                continue

            # Aggregate seconds by (timestamp, mode) without building a huge pivot
            agg = (
                proj.groupby(["timestamp", "mode"], observed=True, sort=False)["value"]
                .sum()
                .unstack(fill_value=0)  # columns: (idle, busy) as present
            )

            # Grab columns safely if one is missing
            idle_seconds = agg.get("idle", 0.0)
            busy_seconds = agg.get("busy", 0.0)

            # Compute Wh (J = W*s; 1 Wh = 3600 J)
            estimated_watt_hours = (idle_seconds * IDLE_WATTAGE + busy_seconds * BUSY_WATTAGE) / 3600.0

            # Build result frame, keep memory small
            project_result = (
                pd.DataFrame(
                    {
                        "timestamp": estimated_watt_hours.index.values,
                        "estimated_watt_hours": estimated_watt_hours.values.astype("float32"),
                        "project_name": project,
                    }
                )
                .reset_index(drop=True)
            )

            all_projects.append(project_result)

            # Free per-project intermediates
            del proj, agg, idle_seconds, busy_seconds, estimated_watt_hours
            gc.collect()

        if not all_projects:
            print("No usage data was processed. Output file will not be created.")
            return

        final_df = pd.concat(all_projects, ignore_index=True)

        # Reorder columns for clarity
        final_df = final_df[["project_name", "timestamp", "estimated_watt_hours"]]

        # Ensure timestamp remains UTC-naive (already done), and types are compact
        final_df["project_name"] = final_df["project_name"].astype("category")
        final_df["estimated_watt_hours"] = final_df["estimated_watt_hours"].astype("float32")

        try:
            print(f"Saving estimated electricity usage to '{OUTPUT_FILE}'...")
            # Save with pyarrow; timestamps are UTC-naive -> no timezone metadata
            final_df.to_parquet(OUTPUT_FILE, engine="pyarrow")
            print(f"Successfully created '{OUTPUT_FILE}' with {len(final_df):,} records.")
        except Exception as e:
            print(f"An error occurred while saving the output file: {e}")
