import json
from datetime import datetime
import os



def save_estimated_project_usage_entry(cloud_project_name, entry):
    # Get Year, Month, Day, hour from datetime object
    year = entry.timestamp.year
    month = entry.timestamp.month
    day = entry.timestamp.day
    hour = entry.timestamp.hour
    # Construct filepath
    subfolder = "data/estimated_project_usage/" + cloud_project_name + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/"
    file = subfolder + str(hour) + ".json"

    # Create the file if it doesn't exist
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)

    # Save the entry to the file
    with open(file, "w") as f:
        json.dump(entry.construct_json(), f)