import datetime as dt
import requests

def get_forecast():

    now = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start = now.isoformat(timespec="minutes") + "Z"   

    url = f"https://api.carbonintensity.org.uk/intensity/{start}/fw48h"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()["data"]          
    except requests.RequestException as e:
        print(f"API error: {e} — response was {r.text}")
        return []

if __name__ == "__main__":
    forecast = get_forecast()
    print(f"{len(forecast)=}")
