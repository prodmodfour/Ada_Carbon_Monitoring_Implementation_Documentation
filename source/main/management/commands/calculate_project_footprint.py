from django.core.management.base import BaseCommand
import pandas as pd
import requests
from datetime import timedelta
import time

# pyarrow is needed for .to_parquet(engine="pyarrow")
import pyarrow  # noqa: F401


class Command(BaseCommand):
    help = "Calculate project carbon footprint using regional carbon intensity data."

    def handle(self, *args, **kwargs):
        print("Starting calculation of project carbon footprint.", flush=True)

        INPUT_FILE = "project_estimated_electricity_usage.parquet"
        OUTPUT_FILE = "project_carbon_footprint.parquet"

        # Carbon Intensity API constants
        REGION_ID = 12  # South England
        API_BASE_URL = "https://api.carbonintensity.org.uk"

        # ---------------------------
        # Load usage parquet (UTC-naive expected; tolerate tz-aware)
        # ---------------------------
        try:
            print(f"Loading electricity usage data from '{INPUT_FILE}'...", flush=True)
            df = pd.read_parquet(INPUT_FILE)
            if df.empty:
                print("Warning: Input file is empty. No footprint to calculate.", flush=True)
                return

            expected = {"project_name", "timestamp", "estimated_watt_hours"}
            missing = expected - set(df.columns)
            if missing:
                print(f"Error: Input file is missing required columns: {missing}", flush=True)
                return

            # Normalize timestamp: ensure UTC then floor to 30-minute bins
            ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            if ts.isna().any():
                bad = int(ts.isna().sum())
                print(f"Warning: {bad} rows had invalid timestamps and will be dropped.", flush=True)
            df = df[~ts.isna()].copy()
            df["timestamp"] = ts[~ts.isna()]

            # Use '30min' (avoid deprecated 'T')
            df["intensity_timestamp"] = df["timestamp"].dt.floor("30min")
            print("Data loaded and timestamps normalized to UTC (30-minute bins).", flush=True)
        except FileNotFoundError:
            print(
                f"Error: Input file '{INPUT_FILE}' not found. "
                "Please run the 'calculate_project_usage' command first.",
                flush=True,
            )
            return
        except Exception as e:
            print(f"An error occurred while reading the Parquet file: {e}", flush=True)
            return

        if df.empty:
            print("No rows remain after timestamp normalization; exiting.", flush=True)
            return

        # ---------------------------
        # Build chunked API windows (UTC Z)
        # ---------------------------
        start_bound = df["timestamp"].min().floor("30min")
        end_bound = df["timestamp"].max().ceil("30min")  # include last half-hour

        # Some regional API responses send an error string in "data" if range too large.
        # Be conservative: 7-day chunks to avoid edge cases.
        CHUNK_DAYS = 7
        STEP = timedelta(days=CHUNK_DAYS)

        windows = []
        cursor = start_bound
        while cursor < end_bound:
            nxt = min(cursor + STEP, end_bound)
            # Guard against zero-length windows (can happen with equal bounds)
            if nxt <= cursor:
                nxt = cursor + timedelta(minutes=30)
                if nxt > end_bound:
                    break
            windows.append((cursor, nxt))
            cursor = nxt

        if not windows:
            print("No time windows to query; exiting.", flush=True)
            return

        print(
            f"Fetching carbon intensity in {len(windows)} window(s) of up to {CHUNK_DAYS} days each.",
            flush=True,
        )

        # ---------------------------
        # Fetch + parse API response per chunk with simple retries
        # ---------------------------
        all_intensity = []

        def to_iso_z(ts):
            return ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        def extract_records(payload, region_id):
            """
            Return a list of half-hourly records with keys including:
              - 'from' (timestamp)
              - 'intensity' (dict or number)
            Payload shapes vary; this function tolerates several.
            """
            if not isinstance(payload, dict):
                return None, "payload-not-dict"

            data = payload.get("data", None)

            # If the API returns a message or string in 'data', bail out gracefully
            if isinstance(data, str):
                return None, f"data-string:{data[:80]}"

            # Common/expected: list of region blocks
            if isinstance(data, list):
                # Keep only dict elements
                dict_blocks = [b for b in data if isinstance(b, dict)]
                if not dict_blocks:
                    return None, "data-list-without-dicts"

                # First, try to find a block whose regionid matches
                region_block = None
                for b in dict_blocks:
                    if str(b.get("regionid")) == str(region_id):
                        region_block = b
                        break

                # If not found, take the first block that has a 'data' list
                if region_block is None:
                    for b in dict_blocks:
                        if isinstance(b.get("data"), list):
                            region_block = b
                            break

                if region_block is None:
                    # As a last resort, pick the first dict
                    region_block = dict_blocks[0]

                records = region_block.get("data")
                if isinstance(records, list):
                    return records, "ok-list"

                # Some shapes may nest under different key names (very rare)
                for alt in ("values", "records"):
                    records = region_block.get(alt)
                    if isinstance(records, list):
                        return records, f"ok-{alt}"

                return None, "region-block-without-record-list"

            # Another occasional shape: 'data' is a dict with its own 'data' list
            if isinstance(data, dict):
                nested = data.get("data")
                if isinstance(nested, list):
                    return nested, "ok-nested-list"
                # Or nested under a region map
                regions = data.get("regions")
                if isinstance(regions, list):
                    for r in regions:
                        if isinstance(r, dict) and str(r.get("regionid")) == str(region_id):
                            recs = r.get("data")
                            if isinstance(recs, list):
                                return recs, "ok-regions-list"
                return None, "data-dict-without-list"

            # Unknown shape
            return None, f"unknown-type:{type(data).__name__}"

        for i, (w_start, w_end) in enumerate(windows, 1):
            start_iso = to_iso_z(w_start)
            end_iso = to_iso_z(w_end)
            api_url = f"{API_BASE_URL}/regional/intensity/{start_iso}/{end_iso}/regionid/{REGION_ID}"

            print(f"[{i}/{len(windows)}] {start_iso} → {end_iso}", flush=True)

            tries, max_tries = 0, 3
            payload = None
            while tries < max_tries:
                tries += 1
                try:
                    resp = requests.get(api_url, timeout=10)
                    # Retry on 429/5xx
                    if resp.status_code >= 500 or resp.status_code == 429:
                        raise requests.exceptions.HTTPError(f"{resp.status_code} upstream")
                    resp.raise_for_status()
                    payload = resp.json()
                    break
                except requests.exceptions.HTTPError as e:
                    if (resp.status_code >= 500 or resp.status_code == 429) and tries < max_tries:
                        backoff = 2 ** tries
                        print(f"  Server/Rate error ({e}); retrying in {backoff}s...", flush=True)
                        time.sleep(backoff)
                        continue
                    print(f"  Skipping window due to HTTP error: {e}", flush=True)
                    payload = None
                    break
                except requests.exceptions.RequestException as e:
                    if tries < max_tries:
                        backoff = 2 ** tries
                        print(f"  Network error ({e}); retrying in {backoff}s...", flush=True)
                        time.sleep(backoff)
                        continue
                    print(f"  Skipping window due to network error: {e}", flush=True)
                    payload = None
                    break

            if not payload:
                continue

            records, status = extract_records(payload, REGION_ID)
            if records is None:
                print(f"  Unexpected payload shape ({status}); skipping this window.", flush=True)
                continue

            try:
                df_chunk = pd.DataFrame(records)

                # Some API variants provide 'intensity' as a number; others as a dict with 'actual'/'forecast'
                def _pick_intensity(obj):
                    if isinstance(obj, dict):
                        return obj.get("actual", obj.get("forecast"))
                    # If it's already a number
                    return obj

                if "intensity" not in df_chunk.columns:
                    print("  Error: API data missing 'intensity'; skipping this window.", flush=True)
                    continue

                df_chunk["carbon_intensity"] = df_chunk["intensity"].apply(_pick_intensity)

                # Require a valid timestamp column
                ts_col = None
                for candidate in ("from", "datetime", "timestamp"):
                    if candidate in df_chunk.columns:
                        ts_col = candidate
                        break

                if ts_col is None:
                    print("  Error: API data missing timestamps; skipping this window.", flush=True)
                    continue

                df_chunk = df_chunk[[ts_col, "carbon_intensity"]].rename(
                    columns={ts_col: "intensity_timestamp"}
                )
                df_chunk["intensity_timestamp"] = (
                    pd.to_datetime(df_chunk["intensity_timestamp"], utc=True, errors="coerce")
                    .dt.floor("30min")
                )
                df_chunk = df_chunk.dropna(subset=["intensity_timestamp"])

                # Some windows may return no rows (e.g., maintenance)
                if df_chunk.empty:
                    print("  No half-hour rows returned for this window.", flush=True)
                    continue

                print(f"  Collected {len(df_chunk)} half-hour rows. [{status}]", flush=True)
                all_intensity.append(df_chunk)
            except Exception as e:
                print(f"  Error parsing API response for this window: {e}", flush=True)

        if not all_intensity:
            print("No carbon intensity data retrieved for any window; exiting.", flush=True)
            return

        intensity_df = pd.concat(all_intensity, ignore_index=True)
        # De-dupe on the join key, preferring later rows (actual over forecast)
        intensity_df = (
            intensity_df.sort_values("intensity_timestamp").drop_duplicates(
                subset=["intensity_timestamp"], keep="last"
            )
        )

        # ---------------------------
        # Join & compute footprint
        # ---------------------------
        merged = pd.merge(df, intensity_df, on="intensity_timestamp", how="left")

        missing = merged["carbon_intensity"].isna().sum()
        if missing:
            print(
                f"Warning: No carbon intensity for {missing} of {len(merged)} rows. "
                "Dropping those rows before footprint calculation.",
                flush=True,
            )
            merged = merged.dropna(subset=["carbon_intensity"])

        if merged.empty:
            print("No rows available after aligning with carbon intensity data.", flush=True)
            return

        merged["estimated_kwh"] = merged["estimated_watt_hours"] / 1000.0
        merged["carbon_footprint_gCO2e"] = merged["estimated_kwh"] * merged["carbon_intensity"]

        final_df = merged[["project_name", "timestamp", "carbon_footprint_gCO2e"]].copy()

        # ---------------------------
        # Save
        # ---------------------------
        try:
            print(f"Saving carbon footprint data to '{OUTPUT_FILE}'.", flush=True)
            final_df.to_parquet(OUTPUT_FILE, engine="pyarrow")
            print(f"Successfully created '{OUTPUT_FILE}' with {len(final_df)} records.", flush=True)
        except Exception as e:
            print(f"An error occurred while saving the output file: {e}", flush=True)
