import time
import requests
from prometheus_api_client import PrometheusConnect
from database import add_reading 

PROMETHEUS_URL = "https://host-172-16-100-248.nubes.stfc.ac.uk"
CARBON_INTENSITY_API_URL = "https://api.carbonintensity.org.uk/intensity"
MONITORING_INTERVAL_SECONDS = 60
IDLE_POWER_WATTS = 50.0
WATTS_PER_CORE = 20.0
WATTS_PER_GB_MEM = 0.4
TARGET_METRICS = {
    'cpu_seconds_total': 'node_cpu_seconds_total',
    'memory_active_bytes': 'node_memory_Active_bytes',
}

def connect_to_prometheus(url: str):
    try:
        prom = PrometheusConnect(url=url, disable_ssl=True)
        if prom.check_prometheus_connection():
            return prom
    except Exception as e:
        print(f"[Data Logger] Error connecting to Prometheus: {e}")
    return None

def fetch_latest_metrics(prom_connection: PrometheusConnect) -> dict:
    latest_values = {}
    for key, metric_name in TARGET_METRICS.items():
        try:
            metric_data = prom_connection.get_current_metric_value(metric_name)
            if metric_data:
                latest_values[key] = float(metric_data[0]['value'][1])
            else: latest_values[key] = 0
        except Exception: latest_values[key] = 0
    return latest_values

def get_carbon_intensity() -> int:
    try:
        response = requests.get(CARBON_INTENSITY_API_URL)
        response.raise_for_status()
        data = response.json()
        actual_intensity = data['data'][0]['intensity']['actual']
        return actual_intensity if actual_intensity is not None else data['data'][0]['intensity']['forecast']
    except Exception: return 0

def estimate_power_watts(metrics: dict, previous_metrics: dict) -> float:
    cpu_seconds_used = metrics.get('cpu_seconds_total', 0) - previous_metrics.get('cpu_seconds_total', metrics.get('cpu_seconds_total', 0))
    average_cores_used = cpu_seconds_used / MONITORING_INTERVAL_SECONDS
    cpu_watts = average_cores_used * WATTS_PER_CORE
    memory_in_gb = metrics.get('memory_active_bytes', 0) / (1024 * 1024 * 1024)
    memory_watts = memory_in_gb * WATTS_PER_GB_MEM
    return IDLE_POWER_WATTS + cpu_watts + memory_watts



def start_logging():

    print("[Data Logger] Starting data logging thread...")
    prom_client = connect_to_prometheus(PROMETHEUS_URL)
    
    if not prom_client:
        print("[Data Logger] Could not connect to Prometheus. Logging aborted.")
        return

    previous_metrics_data = fetch_latest_metrics(prom_client)
    
    while True:
        try:
            time.sleep(MONITORING_INTERVAL_SECONDS)
            
            current_metrics_data = fetch_latest_metrics(prom_client)
            carbon_intensity_gco2_kwh = get_carbon_intensity()

            if current_metrics_data and carbon_intensity_gco2_kwh > 0:
                estimated_watts = estimate_power_watts(current_metrics_data, previous_metrics_data)
                interval_in_hours = MONITORING_INTERVAL_SECONDS / 3600
                energy_kwh = (estimated_watts * interval_in_hours)
                grams_co2_eq = energy_kwh * carbon_intensity_gco2_kwh
                

                add_reading(estimated_watts, carbon_intensity_gco2_kwh, grams_co2_eq)
                print(f"[Data Logger] Logged new reading to DB: {grams_co2_eq:.4f} gCO2eq")

                previous_metrics_data = current_metrics_data
            else:
                print("[Data Logger] Could not retrieve data. Skipping DB entry.")
            
        except Exception as e:
            print(f"[Data Logger] An error occurred in the logging loop: {e}")
            time.sleep(MONITORING_INTERVAL_SECONDS)