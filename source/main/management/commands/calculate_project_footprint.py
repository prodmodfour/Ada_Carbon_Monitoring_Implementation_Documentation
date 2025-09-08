from django.core.management.base import BaseCommand
import pandas as pd
import requests
import pyarrow  # needed by .to_parquet(engine="pyarrow")

class Command(BaseCommand):
    help = "Calculate project carbon footprint using regional carbon intensity data."

    def handle(self, *args, **kwargs):
        print("Starting calculation of project carbon footprint.")

        INPUT_FILE = "project_estimated_electricity_usage.parquet"
        OUTPUT_FILE = "project_carbon_footprint.parquet"

        # Carbon Intensity API constants
        # Region 12 is South England
        REGION_ID = 12
        API_BASE_URL = "https://api.carbonintensity.org.uk"

        # ---------------------------
        # Load usage parquet (UTC)
        # ---------------------------
        try:
            print(f"Loading electricity usage data from '{INPUT_FILE}'...")
            df = pd.read_parquet(INPUT_FILE)
            if df.empty:
                print("Warning: Input file is empty. No footprint to calculate.")
                return
            # Ensure expected columns exist
            expected = {"project_name", "timestamp", "estimated_watt_hours"}
            missing = expected - set(df.columns)
            if missing:
                print(f"Error: Input file is missing required columns: {missing}")
                return

            # Make timestamps UTC-aware and aligned to 30-min bins for joining
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df["intensity_timestamp"] = df["timestamp"].dt.floor("30T")
            print("Data loaded and timestamps normalized to UTC.")
        except FileNotFoundError:
            print(
                f"Error: Input file '{INPUT_FILE}' not found. "
                "Please run the 'calculate_project_usage' command first."
            )
            return
        except Exception as e:
            print(f"An error occurred while reading the Parquet file: {e}")
            return

        # ---------------------------
        # Build API window (UTC Z)
        # ---------------------------
        start_ts = df["timestamp"].min()
        end_ts = df["timestamp"].max()
        # Format with trailing 'Z' for Carbon Intensity API
        start_iso = start_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = end_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        api_url = (
            f"{API_BASE_URL}/regional/intensity/{start_iso}/{end_iso}/regionid/{REGION_ID}"
        )
        print(f"Fetching carbon intensity data for region ID {REGION_ID}.")
        print(f"API URL: {api_url}")

        # ---------------------------
        # Fetch + parse API response
        # ---------------------------
        try:
            # Add timeout; simple single attempt (could add retries if needed)
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            payload = response.json()

            # Defensive parsing:
            # Some responses nest like: {"data": [{ "regionid": 12, "data": [ ... ] }]}
            # We prefer the entry that matches our REGION_ID, else fall back to first.
            data_list = payload.get("data", [])
            if not data_list:
                print("Warning: Carbon intensity API returned no top-level 'data'.")
                return

            # Try to find the matching region; if the endpoint already filters by region,
            # this will just return the first item.
            region_block = None
            for block in data_list:
                if str(block.get("regionid")) == str(REGION_ID):
                    region_block = block
                    break
            if region_block is None:
                region_block = data_list[0]

            intensity_records = region_block.get("data", [])
            if not intensity_records:
                print("Warning: Carbon intensity API returned no records for the window.")
                return

            print(f"Successfully fetched {len(intensity_records)} carbon intensity records.")

            # Build intensity dataframe
            intensity_df = pd.DataFrame(intensity_records)

            # Extract 'actual' if present; otherwise use 'forecast'
            def _pick_intensity(obj):
                if not isinstance(obj, dict):
                    return None
                return obj.get("actual", obj.get("forecast"))

            intensity_df["carbon_intensity"] = intensity_df["intensity"].apply(_pick_intensity)

            # Keep start-of-interval ('from') and intensity, normalize to UTC and 30-min floor
            if "from" not in intensity_df.columns:
                print("Error: API data missing 'from' timestamps.")
                return

            intensity_df = intensity_df[["from", "carbon_intensity"]].rename(
                columns={"from": "intensity_timestamp"}
            )
            intensity_df["intensity_timestamp"] = pd.to_datetime(
                intensity_df["intensity_timestamp"], utc=True
            ).dt.floor("30T")

            # Drop duplicates on the join key keeping the last (usually 'actual' overwrites forecast)
            intensity_df = intensity_df.sort_values("intensity_timestamp").drop_duplicates(
                subset=["intensity_timestamp"], keep="last"
            )

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Carbon Intensity API: {e}")
            return
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error parsing API response structure: {e}")
            return

        # ---------------------------
        # Join & compute footprint
        # ---------------------------
        merged = pd.merge(df, intensity_df, on="intensity_timestamp", how="left")

        # Report missing matches for observability
        missing = merged["carbon_intensity"].isna().sum()
        if missing:
            print(
                f"Warning: No carbon intensity for {missing} of {len(merged)} rows. "
                "Dropping those rows before footprint calculation."
            )
            merged = merged.dropna(subset=["carbon_intensity"])

        if merged.empty:
            print("No rows available after aligning with carbon intensity data.")
            return

        # Convert Wh -> kWh, then multiply by gCO2/kWh to get gCO2e
        merged["estimated_kwh"] = merged["estimated_watt_hours"] / 1000.0
        merged["carbon_footprint_gCO2e"] = merged["estimated_kwh"] * merged["carbon_intensity"]

        # Prepare final output
        final_df = merged[["project_name", "timestamp", "carbon_footprint_gCO2e"]].copy()

        # ---------------------------
        # Save
        # ---------------------------
        try:
            print(f"Saving carbon footprint data to '{OUTPUT_FILE}'.")
            final_df.to_parquet(OUTPUT_FILE, engine="pyarrow")
            print(f"Successfully created '{OUTPUT_FILE}' with {len(final_df)} records.")
        except Exception as e:
            print(f"An error occurred while saving the output file: {e}")
