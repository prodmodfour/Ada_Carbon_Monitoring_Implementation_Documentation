from datetime import datetime, timedelta
import typing
from prometheus.PrometheusAPIClient import PrometheusAPIClient
from prometheus import prometheus_queries
from usage_calculation import usage_calculation_functions
from usage_calculation.CarbonIntensityAPIClient import CarbonIntensityAPIClient
import os
import json

def download_cpu_seconds_total(start_date: str = None, end_date: str = None):
    # Input dates are in the format DD_MM_YYYY

    # If no start date is provided, set it to 1 year ago
    if start_date is None:
        start_date = datetime.now() - timedelta(days=185)
    else:
        start_date = datetime.strptime(start_date, '%d_%m_%Y')
    
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%d_%m_%Y')

    # Calculate the number of days between the start and end dates
    number_days = (end_date - start_date).days + 1
    print(f"number_days to download: {number_days}")

    # Set up API client
    prometheus_client = PrometheusAPIClient()

    # Loop through each day and download the data
    for day in range(number_days):
        date = start_date + timedelta(days=day)
        print(date)

        # Download the data for the current day
        download_cpu_seconds_total_for_day(date, prometheus_client)

def download_cpu_seconds_total_for_day(datetime_to_download: datetime, prometheus_client: PrometheusAPIClient):
    project_labels = [ "CDAaaS", "IDAaaS"]
    datetime_to_download = datetime_to_download.replace(hour=0, minute=0, second=0, microsecond=0)

    project_data_timeseries = dict()
    machine_data_timeseries = dict()
    
    
    for hour in range(24):
        if datetime_to_download >= datetime.now():
            break

        for project_label in project_labels:
            response = prometheus_queries.cpu_seconds_total(prometheus_client, datetime_to_download, project_label)
            if not response:
                continue
            project_data, machine_data = parse_prometheus_response(response, datetime_to_download)

            _add_to_project_data_timeseries(project_data, project_data_timeseries, datetime_to_download)
            _add_to_machine_data_timeseries(machine_data, machine_data_timeseries, datetime_to_download)
        datetime_to_download += timedelta(hours=1)

    _save_project_data_day_entry(project_data_timeseries, datetime_to_download, project_label)
    _save_machine_data_day_entry(machine_data_timeseries, datetime_to_download, project_label)



        
        
def _determine_machine_label_and_cpu_mode(series: dict):
        machine_label = None
        cpu_mode = None
        for label_name, label_value in series["metric"].items():
            if label_name == "machine_name":
                machine_label = label_value
            if label_name == "mode":
                cpu_mode = label_value
        
        return machine_label, cpu_mode



def parse_prometheus_response(response: dict, datetime: datetime):
    project_data = {
        "busy_cpu_seconds_total": 0,
        "idle_cpu_seconds_total": 0,
        "busy_kwh": 0,
        "idle_kwh": 0,
        "intensity_gCo2eq/kwh": 0,
        "busy_gCo2eq": 0,
        "idle_gCo2eq": 0
    }
    machine_data = dict()

    _determine_usage_data_from_prometheus_response(response, machine_data, project_data, datetime)

    return project_data, machine_data

def _determine_usage_data_from_prometheus_response(response: dict, machine_data: dict, project_data: dict, datetime: datetime):
    carbon_intensity_api_client = CarbonIntensityAPIClient()
    
    carbon_intensity = carbon_intensity_api_client.get_carbon_intensity(datetime)
    for series in response["data"]["result"]:
        machine_label, cpu_mode = _determine_machine_label_and_cpu_mode(series)

        if machine_label == None:
            continue
        if machine_label not in machine_data.keys():
            machine_data[machine_label] = {
                "busy_cpu_seconds_total": 0,
                "idle_cpu_seconds_total": 0,
                "busy_kwh": 0,
                "idle_kwh": 0,
                "intensity_gCo2eq/kwh": 0,
                "busy_gCo2eq": 0,
                "idle_gCo2eq": 0
            }

        
        machine_data[machine_label]["intensity_gCo2eq/kwh"] = carbon_intensity
        project_data["intensity_gCo2eq/kwh"] = carbon_intensity

        cpu_seconds = float(series["values"][0][1])
        if cpu_mode == "idle":
            machine_data[machine_label]["idle_cpu_seconds_total"] += cpu_seconds
            project_data["idle_cpu_seconds_total"] += cpu_seconds

            idle_kwh = usage_calculation_functions.estimate_electricity_usage_kwh(cpu_seconds, 0.1)
            machine_data[machine_label]["idle_kwh"] += idle_kwh
            project_data["idle_kwh"] += idle_kwh

            idle_gCo2eq = usage_calculation_functions.estimate_carbon_footprint_gCO2eq(idle_kwh, carbon_intensity)
            machine_data[machine_label]["idle_gCo2eq"] += idle_gCo2eq
            project_data["idle_gCo2eq"] += idle_gCo2eq
        elif cpu_mode != "idle":
            machine_data[machine_label]["busy_cpu_seconds_total"] += cpu_seconds
            project_data["busy_cpu_seconds_total"] += cpu_seconds

            busy_kwh = usage_calculation_functions.estimate_electricity_usage_kwh(cpu_seconds, 12)
            machine_data[machine_label]["busy_kwh"] += busy_kwh
            project_data["busy_kwh"] += busy_kwh

            busy_gCo2eq = usage_calculation_functions.estimate_carbon_footprint_gCO2eq(busy_kwh, carbon_intensity)
            machine_data[machine_label]["busy_gCo2eq"] += busy_gCo2eq
            project_data["busy_gCo2eq"] += busy_gCo2eq


def _add_to_project_data_timeseries(project_data: dict, project_data_timeseries: dict, datetime: datetime):
    time_string = datetime.strftime("%H:%M")
    project_data_timeseries[time_string] = project_data

def _add_to_machine_data_timeseries(machine_data: dict, machine_data_timeseries: dict, datetime: datetime):
    time_string = datetime.strftime("%H:%M")
    machine_data_timeseries[time_string] = machine_data
    

def _save_project_data_day_entry(project_data_timeseries: dict, datetime_to_download: datetime, project_label: str):
    if not project_data_timeseries:
        return

    folder_name = f"data/{datetime_to_download.strftime("%m/%d")}"
    
    # Create the directory if it does not already exist
    os.makedirs(folder_name, exist_ok=True)
    
    # Construct the full file path using the folder and project label
    file_path = os.path.join(folder_name, f"{project_label}_timeseries.json")
    
    # Write the dictionary to the specified JSON file
    with open(file_path, 'w') as json_file:
        json.dump(project_data_timeseries, json_file, indent=4)

def _save_machine_data_day_entry(machine_data_timeseries: dict, datetime_to_download: datetime, project_label: str):
    if not machine_data_timeseries:
        return
    
    folder_name = f"data/{datetime_to_download.strftime("%m/%d")}"
    
    # Create the directory if it does not already exist
    os.makedirs(folder_name, exist_ok=True)
    
    # Construct the full file path using the folder and project label
    file_path = os.path.join(folder_name, f"{project_label}_machine_timeseries.json")
    
    # Write the dictionary to the specified JSON file
    with open(file_path, 'w') as json_file:
        json.dump(machine_data_timeseries, json_file, indent=4)


if __name__ == "__main__":
    download_cpu_seconds_total()