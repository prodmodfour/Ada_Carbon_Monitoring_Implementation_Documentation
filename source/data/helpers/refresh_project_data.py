from datetime import datetime
import pyarrow
from pyarrow import parquet
import pandas as pd
from data.helpers.PrometheusAPIClient import PrometheusAPIClient
import requests

def refresh_project_data(cloud_project_name, start_timestamp, end_timestamp):
    print(f"Refreshing data for {cloud_project_name}")
    # Convert timestamps to UNIX Milliseconds
    start_timestamp = int(start_timestamp.timestamp() * 1000)
    end_timestamp = int(end_timestamp.timestamp() * 1000)

    print("Converted timestamps to UNIX Milliseconds")
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
    
    current_timestamp = start_timestamp
    while current_timestamp < end_timestamp:
        # Convert current timestamp to datetime
        current_timestamp_datetime = datetime.fromtimestamp(current_timestamp / 1000)
        print(f"Current timestamp: {current_timestamp_datetime}")

        # Query the Prometheus database for the data
        step = "1h" 
        query = f'increase(node_cpu_seconds_total{{cloud_project_name="{cloud_project_name}"}}[{step}])'
        

        parameters = {
            "query": query,
            "start": current_timestamp,
            "end": current_timestamp,
            "step": step
        }

        response = prometheus_client.query(parameters)
        if response is None:
            current_timestamp += 3600000
            continue
        
        


        current_timestamp += 3600000