from datetime import datetime, timedelta
import typing
from prometheus.PrometheusAPIClient import PrometheusAPIClient
from prometheus import prometheus_queries

def download_cpu_seconds_total(start_date: str = None, end_date: str = None):
    # Input dates are in the format DD_MM_YYYY

    # If no start date is provided, set it to 1 year ago
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    else:
        start_date = datetime.strptime(start_date, '%d_%m_%Y')
    
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%d_%m_%Y')

    # Calculate the number of days between the start and end dates
    number_days = (end_date - start_date).days + 1
    print(number_days)

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
    
    
    for hour in range(24):
        if datetime_to_download >= datetime.now():
            break

        for project_label in project_labels:
            response = prometheus_queries.cpu_seconds_total(prometheus_client, datetime_to_download, project_label)
            project_data, machine_data = parse_prometheus_response(response)
            save_project_data_day_entry(project_data, datetime_to_download, project_label)
            save_machine_data_day_entry(project_data, datetime_to_download, project_label)

            print(project_data)
            print(machine_data)

        print(datetime_to_download)
        datetime_to_download += timedelta(hours=1)

def parse_prometheus_response(response: dict):
    project_data = {
        "busy_kwh": 0,
        "idle_kwh": 0,
    }
    machine_data = dict()

    for series in response["data"]["result"]:
        machine_label = None
        for label_name, label_value in series["metric"].items():
            if label_name == "machine_name":
                machine_label = label_value
        if machine_label is None:
            continue

        if machine_label not in machine_data.keys():
            machine_data[machine_label] = {
                "busy_kwh": 0,
                "idle_kwh": 0,
            }
    # for series in response["data"]["result"]:
    #         if "idle"
    #         machine_data[machine_label]["busy_kwh"] += series["values"][1]
    #         machine_data[machine_label]["idle_kwh"] += series["values"][2]
    #         project_data["busy_kwh"] += series["values"][1]
    #         project_data["idle_kwh"] += series["values"][2]

    
    return project_data, machine_data

def save_project_data_day_entry(project_data: dict, datetime_to_download: datetime, project_label: str):
    pass

def save_machine_data_day_entry(machine_data: dict[str, dict[str, any]], datetime_to_download: datetime, project_label: str):
    pass

if __name__ == "__main__":
    download_cpu_seconds_total_for_day(datetime.now() - timedelta(days=1), PrometheusAPIClient())