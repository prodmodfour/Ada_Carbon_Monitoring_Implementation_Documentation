import requests
from flask import Flask, render_template
from datetime import datetime, timedelta, timezone


try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone as ZoneInfo

app = Flask(__name__)


def get_carbon_intensity_data():
    """
    Fetches current and ~48-hour forecast carbon intensity data for Great Britain
    using a robust method that queries by date.
    """
    try:

        current_url = 'https://api.carbonintensity.org.uk/intensity'
        current_response = requests.get(current_url)
        current_response.raise_for_status()
        current_intensity_data = current_response.json()['data'][0]


        uk_tz = ZoneInfo("Europe/London")
        today = datetime.now(uk_tz)
        tomorrow = today + timedelta(days=1)
        
        today_str = today.strftime('%Y-%m-%d')
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')


        today_forecast_url = f'https://api.carbonintensity.org.uk/intensity/date/{today_str}'
        today_response = requests.get(today_forecast_url)
        today_response.raise_for_status()
        today_data = today_response.json()['data']

     
        tomorrow_forecast_url = f'https://api.carbonintensity.org.uk/intensity/date/{tomorrow_str}'
        tomorrow_response = requests.get(tomorrow_forecast_url)
        tomorrow_response.raise_for_status()
        tomorrow_data = tomorrow_response.json()['data']

  
        full_forecast_data = today_data + tomorrow_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Carbon Intensity API: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response: {e}")
        return None, None

    current_intensity = {
        'actual': current_intensity_data['intensity'].get('actual'),
        'forecast': current_intensity_data['intensity']['forecast'],
        'index': current_intensity_data['intensity']['index']
    }

    now_utc = datetime.now(timezone.utc)
    future_slots = []
    for period in full_forecast_data:

        period_start_time = datetime.fromisoformat(period['from'].replace('Z', '+00:00'))
        if period_start_time > now_utc:
            future_slots.append(period)

    if not future_slots:
        best_time_info = None
    else:
        best_period = min(future_slots, key=lambda x: x['intensity']['forecast'])
        

        utc_time_str = best_period['from']
        utc_datetime = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        local_datetime = utc_datetime.astimezone(uk_tz)

        best_time_info = {
            'time_str': local_datetime.strftime('%-I:%M %p on %A'),
            'intensity': best_period['intensity']['forecast'],
            'index': best_period['intensity']['index']
        }

    return current_intensity, best_time_info



@app.route('/')
def workspace_page():
    current_intensity, best_time_info = get_carbon_intensity_data()
    return render_template(
        'index.html', 
        current_intensity=current_intensity, 
        best_time_info=best_time_info
    )

if __name__ == '__main__':
    app.run(port=5006,debug=True)