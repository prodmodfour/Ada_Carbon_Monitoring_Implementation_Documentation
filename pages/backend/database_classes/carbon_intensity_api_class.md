---
title: Carbon Intensity API Request Class
parent: Database Classes
nav_order: 1
---

# Todo
* Class diagram
* Functionality Examples

# Carbon Intensity API Request Class
We have a Carbon Intensity API request class that handles requests to the Carbon Intensity API. This class is used to get the carbon intensity for a given time period.
```python
import requests
import typing
from datetime import datetime, timedelta

class CarbonIntensityAPIClient:
    def __init__(self):
        self.api_url = "https://api.carbonintensity.org.uk/intensity"

    def get_carbon_intensity(self, start: datetime) -> float | None:
        # Define the end of the first 30-min slot and the end of the hour
        mid_time = start + timedelta(minutes=30)
        end_time = start + timedelta(hours=1)

        # The API expects time in ISO 8601 format (e.g., 2025-09-23T17:00Z)
        # We format the datetime objects into strings for the URL
        start_str = start.strftime('%Y-%m-%dT%H:%MZ')
        mid_str = mid_time.strftime('%Y-%m-%dT%H:%MZ')
        end_str = end_time.strftime('%Y-%m-%dT%H:%MZ')

        # Construct the URLs for the two separate half-hour periods
        url_first_half = f"{self.api_url}/{start_str}/{mid_str}"
        url_second_half = f"{self.api_url}/{mid_str}/{end_str}"

        try:
            # --- Get data for the first half-hour ---
            response1 = requests.get(url_first_half)
            response1.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            data1 = response1.json()
            # The API returns a list of data points; we need the first one.
            intensity1 = data1['data'][0]['intensity']['actual']

            # --- Get data for the second half-hour ---
            response2 = requests.get(url_second_half)
            response2.raise_for_status()
            data2 = response2.json()
            intensity2 = data2['data'][0]['intensity']['actual']

            # --- Calculate and return the average ---
            average_intensity = (intensity1 + intensity2) / 2
            print(f"Average intensity: {average_intensity}")
            return average_intensity


        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return 0
        except (KeyError, IndexError) as e:
            # This can happen if the JSON structure is unexpected or empty
            print(f"Failed to parse data from API response: {e}")
            return 0
```