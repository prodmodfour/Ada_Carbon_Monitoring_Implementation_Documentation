import json
from datetime import datetime
import os
from EstimatedUsageEntry import EstimatedUsageEntry

def construct_estimated_project_usage_file_path(cloud_project_name, timestamp):
    year = timestamp.year
    month = timestamp.month
    day = timestamp.day
    hour = timestamp.hour
    return "data/estimated_project_usage/" + cloud_project_name + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/" + str(hour) + ".json"

def save_estimated_project_usage_entry(cloud_project_name, entry):
    file_path = construct_estimated_project_usage_file_path(cloud_project_name, entry.timestamp)

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
        data = json.load(f)

    # Construct an EstimatedUsageEntry from the json
    entry = EstimatedUsageEntry()
    entry.set_timestamp(datetime.fromisoformat(data["timestamp"]))
    entry.set_cpu_seconds_total(data["busy_cpu_seconds_total"], data["idle_cpu_seconds_total"])
    entry.set_usage_kwh(data["busy_usage_kwh"], data["idle_usage_kwh"])
    entry.set_usage_gCO2eq(data["busy_usage_gCO2eq"], data["idle_usage_gCO2eq"])
    return entry

if __name__ == "__main__":
    print("Testing JSON Functions")
    entry = EstimatedUsageEntry()
    entry.set_timestamp(datetime.now())
    entry.set_cpu_seconds_total(100, 100)
    entry.set_usage_kwh(100, 100)
    entry.set_usage_gCO2eq(100, 100)

    print("Json to save:")
    print(entry.construct_json())
    save_estimated_project_usage_entry("test", entry)
    
    entry = load_estimated_project_usage_entry("test", datetime.now())
    print("Json loaded:")
    print(entry.construct_json())