from datetime import datetime, timedelta, timezone
import pyarrow
from pyarrow import parquet
import pandas as pd
from data.helpers.PrometheusAPIClient import PrometheusAPIClient
import requests
import json
from data.helpers.Machine import Machine

def to_rfc3339(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def refresh_project_data(cloud_project_name, start_timestamp, end_timestamp):
    print(f"Refreshing data for {cloud_project_name}")

    print(f"Start timestamp: {start_timestamp}")
    print(f"End timestamp: {end_timestamp}")

    # Construct filepath
    filepath = f"data/{cloud_project_name}_estimated_usage.parquet"

    # Construct temp file path
    temp_filepath = f"data/{cloud_project_name}_estimated_usage_temp.parquet"

    # Define the schema
    defined_schema = pyarrow.schema([
    pyarrow.field('timestamp', pyarrow.timestamp('ms', tz='UTC'), nullable=False),
    pyarrow.field('busy_usage_cpu_seconds_total', pyarrow.float64()),
    pyarrow.field('idle_usage_cpu_seconds_total', pyarrow.float64()),
    pyarrow.field('busy_usage_kwh', pyarrow.float64()),
    pyarrow.field('idle_usage_kwh', pyarrow.float64()),
    pyarrow.field('busy_usage_gCO2eq', pyarrow.float64()),
    pyarrow.field('idle_usage_gCO2eq', pyarrow.float64()),
    pyarrow.field('status', pyarrow.string(), nullable=False)
    ])

    # Create a dataframe with the schema
    df = pd.DataFrame(columns=defined_schema.names)

    # Create a Prometheus client
    prometheus_url = "https://host-172-16-100-248.nubes.stfc.ac.uk/"
    api_endpoint = "api/v1/query_range"
    prometheus_client = PrometheusAPIClient(prometheus_url, api_endpoint)
    
    #------------------------------------------------------------------------------------------------------------------------------------------
    # Main loop
    #------------------------------------------------------------------------------------------------------------------------------------------
    current_timestamp = start_timestamp
    while current_timestamp < end_timestamp:
        print(f"Current timestamp: {current_timestamp}")

        # Query the Prometheus database for the data
        step = "1h" 
        query = f'increase(node_cpu_seconds_total{{cloud_project_name="{cloud_project_name}"}}[{step}])'
        
        parameters = {
            "query": query,
            "start": to_rfc3339(current_timestamp),
            "end": to_rfc3339(current_timestamp),
            "step": step
        }

        response = prometheus_client.query(parameters)
        if response is None:
            current_timestamp += timedelta(hours=1)
            continue

        # Parse the response
        result = response["data"]["result"]

        busy_cpu_seconds_total = 0
        idle_cpu_seconds_total = 0
        for series in result:
            metrics = series["metric"] # A dictionary of label categories and their values
            value = float(series["values"][0][1]) # The node_cpu_seconds_total value of the series

            if "machine_name" not in metrics.keys():
                continue

            if "mode" not in metrics.keys():
                continue


            machine_name = metrics["machine_name"]
            mode = metrics["mode"]

            if mode == "idle":
                idle_cpu_seconds_total += value
            else:
                busy_cpu_seconds_total += value

        print(f"Busy CPU seconds total: {busy_cpu_seconds_total}")
        print(f"Idle CPU seconds total: {idle_cpu_seconds_total}")


        # Progress
        current_timestamp += timedelta(hours=1)

                    
                        




            
        
    

        # Write to JSON



        current_timestamp += timedelta(hours=1)

    #------------------------------------------------------------------------------------------------------------------------------------------
    # End of main loop
    #------------------------------------------------------------------------------------------------------------------------------------------