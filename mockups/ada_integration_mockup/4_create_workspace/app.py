import requests
from flask import Flask, render_template
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# --- Carbon Intensity API Logic ---
def get_carbon_intensity_data():
    """
    Fetches current and 48-hour forecast carbon intensity data for Great Britain.
    """
    current_intensity_data = None
    forecast_data = None
    
    try:
        # 1. Get current intensity
        # Let requests handle default headers, which is more robust.
        current_url = 'https://api.carbonintensity.org.uk/intensity'
        current_response = requests.get(current_url)
        current_response.raise_for_status()  # Raise an exception for bad status codes (like 400 or 500)
        current_intensity_data = current_response.json()['data'][0]
        
        # 2. Get 48-hour forecast
        forecast_url = 'https://api.carbonintensity.org.uk/intensity/fw48h'
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()['data']

    except requests.exceptions.RequestException as e:
        # This error message will now include the URL that failed.
        print(f"Error fetching data from Carbon Intensity API: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response: {e}")
        return None, None

    # Process current intensity
    current_intensity = {
        'actual': current_intensity_data['intensity'].get('actual'),
        'forecast': current_intensity_data['intensity']['forecast'],
        'index': current_intensity_data['intensity']['index']
    }

    # Find the best (lowest intensity) time in the forecast
    if not forecast_data:
        best_time_info = None
    else:
        # Find the period with the minimum forecasted intensity
        best_period = min(forecast_data, key=lambda x: x['intensity']['forecast'])
        
        # Get the start time of the best period and convert from UTC to local UK time (BST/GMT)
        utc_time_str = best_period['from']
        utc_datetime = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        uk_tz = ZoneInfo("Europe/London")
        local_datetime = utc_datetime.astimezone(uk_tz)

        best_time_info = {
            'time_str': local_datetime.strftime('%-I:%M %p on %A'),
            'intensity': best_period['intensity']['forecast'],
            'index': best_period['intensity']['index']
        }

    return current_intensity, best_time_info


# --- Flask Route ---
@app.route('/')
def workspace_page():
    current_intensity, best_time_info = get_carbon_intensity_data()
    return render_template(
        'index.html', 
        current_intensity=current_intensity, 
        best_time_info=best_time_info
    )

if __name__ == '__main__':
    app.run(debug=True)