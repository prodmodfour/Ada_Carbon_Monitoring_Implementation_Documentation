from django.core.management.base import BaseCommand
import requests
import json
import ada_project.settings
import datetime
import pandas as pd
import pyarrow
import pyarrow.parquet
import os

class Command(BaseCommand):
    help = "Build the database from the prometheus server."

    def handle(self, *arguments, **options):
        print("Building the database from the prometheus server.")
        # I am using python. I want to download data from a prometheus database and store it in Redis. 
        # The time series in question is called node_cpu_seconds_total.
        # It has the following labels: 
        # cloud_project_name (CDAaaS, IDAaaS, DDAaaS)
        # cpu
        # instance
        # job
        # machine_name
        # machine_type_id
        # mode
        # state
        # tag

        # I want to download all of the data in a date range. I want the meta data, the labels, intact and properly attached.
        # default range would be Jan 1 2024 to present day
        # Expect the prometheus server to give 5xx series or 4xx series errors. We should keep the data we have on our first run attempt to copy. 
        # We should fill in gaps in future run attempts.

        # Prometheus server variables
        PROMETHEUS_URL = ada_project.settings.PROMETHEUS_URL
        print("Prometheus URL:")
        print(PROMETHEUS_URL)

        # Query variables
        step = "1h" 
        query = f"increase(node_cpu_seconds_total[{step}])"
        # ISO 8601 format
        # Z means that the time is in UTC
        start_time_in_iso_8601 = "2024-01-01T00:00:00Z" 
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        end_time_in_iso_8601 = now_utc.isoformat().replace('+00:00', 'Z')

        timeout = 60 # seconds

        print("Query variables:")
        print(f"Query: {query}")
        print(f"Start: {start_time_in_iso_8601}")
        print(f"End: {end_time_in_iso_8601}")
        print(f"Step: {step}")
        print(f"Timeout: {timeout}")

        # Create date time variables
        current_datetime = datetime.datetime.fromisoformat(start_time_in_iso_8601.replace('Z', '+00:00'))

        # Create end time
        end_datetime = datetime.datetime.fromisoformat(end_time_in_iso_8601.replace('Z', '+00:00'))


        url = f"{PROMETHEUS_URL}/api/v1/query_range"
        parquet_file_path = "node_cpu_seconds_total.parquet"
        parquet_writer = None
        schema = None

        # Load existing timestamps to avoid re-downloading 
        existing_timestamps = set()
        if os.path.exists(parquet_file_path):
            try:
                # Read only the 'timestamp' column for efficiency
                existing_df = pd.read_parquet(parquet_file_path, columns=['timestamp'])
                # Convert to UTC naive datetime objects and add to a set for fast lookups
                existing_timestamps = set(pd.to_datetime(existing_df['timestamp']).dt.tz_localize(None))
                print(f"Found {len(existing_timestamps)} existing timestamps in '{parquet_file_path}'.")
            except Exception as e:
                print(f"Warning: Could not read existing parquet file at '{parquet_file_path}'. Error: {e}")

        while current_datetime < end_datetime:
            print(f"Current datetime: {current_datetime}")
            # Make current_datetime timezone-naive for comparison
            naive_current_datetime = current_datetime.replace(tzinfo=None)
            if naive_current_datetime in existing_timestamps:
                print(f"Data for {current_datetime} already exists. Skipping.")
                current_datetime += datetime.timedelta(hours=1)
                continue 

            start_time = current_datetime.isoformat()
            end_time = current_datetime + datetime.timedelta(hours=1)
            end_time = end_time.isoformat()

            parameters = {
            "query": query,
            "start": start_time,
            "end": end_time,
            "step": step,
            }

            # Make the request
            response = requests.get(url, params=parameters, timeout=timeout)

            print("URL:", response.url)
            print("Status:", response.status_code, response.reason)

            try:
                response.raise_for_status()  # raises on 4xx/5xx
                print("OK → proceeding to parse JSON")
                data = response.json()
                print("Prometheus status:", data.get("status"))

            except requests.HTTPError as e:
                print("HTTPError:", e)  

                body = e.response.text if e.response is not None else ""
                print("Response body (first 500 chars):")
                print(body[:500])

            # Write to Parquet database
            if data.get("status") == "success" and data.get("data", {}).get("result"):
                all_metrics = []
                for result in data["data"]["result"]:
                    metric_labels = result.get("metric", {})
                    for value_pair in result.get("values", []):
                        record = metric_labels.copy()
                        record['timestamp'] = pd.to_datetime(value_pair[0], unit='s')
                        record['value'] = float(value_pair[1]) # Ensure value is a float
                        all_metrics.append(record)

                if all_metrics:
                    # Convert the list of dictionaries to a pandas DataFrame
                    df = pd.DataFrame(all_metrics)

                    # Convert DataFrame to a PyArrow Table
                    table = pyarrow.Table.from_pandas(df)

                    # --- Write to Parquet ---
                    if parquet_writer is None:
                        # If this is the first batch, create the file and writer
                        schema = table.schema
                        parquet_writer = pyarrow.parquet.ParquetWriter(parquet_file_path, schema)
                    
                    # If the schema of the current batch is different, we have a problem
                    if table.schema != schema:
                        print("Error: Schema of the current batch of data is different from the first batch.")
                        print("This can happen if the metric labels change over time.")
                        # You might want to handle this more gracefully, e.g., by creating a new file
                        # or by trying to align the schemas.
                        break 

                    parquet_writer.write_table(table)
                    print(f"Appended a batch of {len(df)} records to {parquet_file_path}")


            # Progress the current datetime
            current_datetime += datetime.timedelta(hours=1)



        if parquet_writer:
            parquet_writer.close()
            print(f"\nFinished writing data. Parquet file '{parquet_file_path}' is now closed.")
        else:
            print("\nNo data was collected to write to the Parquet file.")

