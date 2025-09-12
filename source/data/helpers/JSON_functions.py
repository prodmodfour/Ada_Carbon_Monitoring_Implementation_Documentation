import json
from datetime import datetime
import os
from data.helpers.EstimatedUsageEntry import EstimatedUsageEntry

def construct_estimated_project_usage_file_path(cloud_project_name, timestamp):
    year = timestamp.year
    month = timestamp.month
    day = timestamp.day
    hour = timestamp.hour
    return "data/estimated_project_usage/" + cloud_project_name + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(hour) + ".json"

def save_estimated_project_usage_entry(cloud_project_name, entry):
    file_path = construct_estimated_project_usage_file_path(cloud_project_name, entry.timestamp)


    # Create the file if it doesn't exist
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path))

    # Save the entry to the file
    with open(file_path, "w") as f:
        f.write(entry.construct_json())

def load_estimated_project_usage_entry(cloud_project_name, timestamp):
    # Construct filepath
    file_path = construct_estimated_project_usage_file_path(cloud_project_name, timestamp)

    # Load the entry from the file
    if not os.path.exists(file_path):
        return EstimatedUsageEntry()

    with open(file_path, "r") as f:
        json = json.load(f)

    # Construct an EstimatedUsageEntry from the json
    entry = EstimatedUsageEntry()
    entry.set_timestamp(json["timestamp"])
    entry.set_cpu_seconds_total(json["busy_cpu_seconds_total"], json["idle_cpu_seconds_total"])
    entry.set_usage_kwh(json["busy_usage_kwh"], json["idle_usage_kwh"])
    entry.set_usage_gCO2eq(json["busy_usage_gCO2eq"], json["idle_usage_gCO2eq"])
    return entry