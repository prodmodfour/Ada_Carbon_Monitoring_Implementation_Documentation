from datetime import datetime, timedelta, timezone
from data.helpers.PrometheusAPIClient import PrometheusAPIClient
import requests
import json
from data.helpers.Machine import Machine
from data.helpers.EstimatedUsageEntry import EstimatedUsageEntry
from data.helpers.JSON_functions import save_estimated_project_usage_entry, load_estimated_project_usage_entry
import typing

def to_rfc3339(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def refresh_project_data(cloud_project_name, start_date: datetime.date, end_date: datetime.date):
    print(f"Refreshing data for {cloud_project_name}")

    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")

    # Create a Prometheus client
    prometheus_url = "https://host-172-16-100-248.nubes.stfc.ac.uk/"
    api_endpoint = "api/v1/query_range"
    prometheus_client = PrometheusAPIClient(prometheus_url, api_endpoint)
    
    #------------------------------------------------------------------------------------------------------------------------------------------
    # Main loop
    #------------------------------------------------------------------------------------------------------------------------------------------
    current_date = start_date
    while current_date < end_date:


        print(f"Current date: {current_date}")


                    
                        

    #------------------------------------------------------------------------------------------------------------------------------------------
    # End of main loop
    #------------------------------------------------------------------------------------------------------------------------------------------