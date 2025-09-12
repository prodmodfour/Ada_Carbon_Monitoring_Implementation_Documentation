import json

def save_estimated_project_usage_entry(cloud_project_name, entry, timestamp):
    # Get Year, Month, Day, hour from Unix Milliseconds timestamp
    year = datetime.fromtimestamp(timestamp / 1000).year
    month = datetime.fromtimestamp(timestamp / 1000).month
    day = datetime.fromtimestamp(timestamp / 1000).day
    hour = datetime.fromtimestamp(timestamp / 1000).hour
    # Construct filepath
    subfolder = "data/estimated_project_usage/" + cloud_project_name + "/" + str(year) + "/" + str(month) + "/" + str(day) + "/"
    file = subfolder + str(hour) + ".json"

    # Create the file if it doesn't exist
    if not os.path.exists(subfolder):
        os.makedirs(subfolder)

    # Save the entry to the file
    with open(file, "w") as f:
        json.dump(entry, f)