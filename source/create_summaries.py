from pathlib import Path
import json
from datetime import datetime, timedelta
import typing

def create_day_summaries():
    start_datetime = datetime(2025, 3, 20, 0, 0, 0)
    data_root_directory = "data"

    current_datetime = start_datetime
    while current_datetime <= datetime.now():
        month = current_datetime.strftime("%m")
        day = current_datetime.strftime("%d")

        base_file_path = f"{data_root_directory}/{month}/{day}/"

        project_labels = ["IDAaaS", "CDAaaS"]

        for project_label in project_labels:
            _summarise_project_day(base_file_path, project_label)
            _summarise_machines_day(base_file_path, project_label)



        current_datetime += timedelta(days=1)

def _summarise_project_day(base_file_path: str, project_label: str):
    file_path = f"{base_file_path}{project_label}_timeseries.json"
    data = None
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' contains invalid JSON.")
    except PermissionError:
        print("Permission error")
    except OSError:
        print("OS Error")

    if data == None:
        return
    busy_kwh = list()
    idle_kwh = list()
    intensities = list()
    busy_gCo2eq = list()
    idle_gCo2eq = list()
    for timestamp, values in data.items():

        busy_kwh.append(values["busy_kwh"])
        idle_kwh.append(values["idle_kwh"])
        intensities.append(values["intensity_gCo2eq/kwh"])
        busy_gCo2eq.append(values["busy_gCo2eq"])
        idle_gCo2eq.append(values["idle_gCo2eq"])

    summary = {
        "total_busy_kwh": sum(busy_kwh),
        "total_idle_kwh": sum(idle_kwh),
        "average_intensity_gCo2eq/kwh": sum(intensities) / len(intensities),
        "total_busy_gCo2eq": sum(busy_gCo2eq),
        "total_idle_gCo2eq": sum(idle_gCo2eq),
        "idle_percentage_kwh": (sum(idle_kwh) / (sum(busy_kwh) + sum(idle_kwh)) * 100),
        "idle_percentage_gCo2eq": (sum(idle_gCo2eq) / (sum(busy_gCo2eq) + sum(idle_gCo2eq)) * 100)
    }

    save_file_path = f"base_file_path{project_label}_summary.json"

    with open(save_file_path, 'w') as json_file:
        json.dump(summary, json_file, indent=4)


def _summarise_machines_day(base_file_path: str, project_label: str):
    file_path = f"{base_file_path}{project_label}_timeseries.json"
    data = None
  
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' contains invalid JSON.")
    except PermissionError:
        print("Permission error")
    except OSError:
        print("OS Error")

    if data == None:
        return
  
    busy_kwh = list()
    idle_kwh = list()
    intensities = list()
    busy_gCo2eq = list()
    idle_gCo2eq = list()

    machine_totals = dict()
    for timestamp, machine_data in data.items():
        for machine_name, values in machine_data:
            if machine_name not in machine_totals.keys():
                machine_totals[machine_name] = {
                    "busy_kwh" = list(),
                    "idle_kwh" = list(),
                    "intensities" = list(),
                    "busy_gCo2eq" = list(),
                    "idle_gCo2eq" = list(),
                }
            machine_totals[machine_name]["busy_kwh"].append(values["busy_kwh"])
            machine_totals[machine_name]["idle_kwh"].append(values["idle_kwh"])
            machine_totals[machine_name]["indensities"].append(values["intensity_gCo2eq/kwh"])
            machine_totals[machine_name]["busy_gCo2eq"].append(values["busy_gCo2eq"])
            machine_totals[machine_name]["idle_gCo2eq"].append(values["idle_gCo2eq"])


    for machine_name in machine_totals.keys():
        sum_busy_kwh = sum(machine_totals[machine_name]["busy_kwh"])
        sum_idle_kwh = sum(machine_totals[machine_name]["idle_kwh"])
        sum_intensities = sum(machine_totals[machine_name]["intensities"])
        sum_busy_gCo2eq = sum(machine_totals[machine_name]["busy_gCo2eq"])
        sum_idle_gCo2eq = sum(machine_totals[machine_name]["idle_gCo2eq"])
        summary = {
            "total_busy_kwh": sum_busy_kwh,
            "total_idle_kwh": sum_idle_kwh,
            "average_intensity_gCo2eq/kwh": sum_intensities / len(sum_intensities),
            "total_busy_gCo2eq": sum_busy_gCo2eq,
            "total_idle_gCo2eq": sum_idle_gCo2eq,
            "idle_percentage_kwh": (sum_idle_kwh / (sum_busy_kwh + sum_idle_kwh) * 100),
            "idle_percentage_gCo2eq": (sum_idle_gCo2eq / (sum_busy_gCo2eq + sum_idle_gCo2eq) * 100)
        }

        save_file_path = f"{base_file_path}{project_label}_{machine_name}_machine_summary.json"

        with open(save_file_path, 'w') as json_file:
            json.dump(summary, json_file, indent=4)

    

if __name__== "__main__":
    create_day_summaries()