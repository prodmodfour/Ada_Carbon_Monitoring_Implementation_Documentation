import time
import os
import requests
from prometheus_api_client import PrometheusConnect

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "https://host-172-16-100-248.nubes.stfc.ac.uk")
CARBON_INTENSITY_API_URL = "https://api.carbonintensity.org.uk/intensity"
MONITORING_INTERVAL_SECONDS = 60

# Hardware assumptions
# These values are estimates for a typical server.
# A modern server might idle around 50-100W.
IDLE_POWER_WATTS = 50.0 
# A single busy CPU core can consume 15-25W. 
WATTS_PER_CORE = 20.0 
# DDR4 RAM uses roughly 0.35-0.5W per GB.
WATTS_PER_GB_MEM = 0.4

TARGET_METRICS = {
    'cpu_seconds_total': 'node_cpu_seconds_total',
    'memory_active_bytes': 'node_memory_Active_bytes',
}




def connect_to_prometheus(url: str):
    """Establishes a connection to the Prometheus server."""
    try:
        print(f"Connecting to Prometheus at {url}...")
        prom = PrometheusConnect(url=url, disable_ssl=True)
        if prom.check_prometheus_connection():
            print("Successfully connected to Prometheus.")
            return prom
    except Exception as e:
        print(f"Error connecting to Prometheus: {e}")
    return None

def fetch_latest_metrics(prom_connection: PrometheusConnect) -> dict:
    """Fetches the latest value for each of our target metrics."""
    latest_values = {}
    print("Fetching latest metrics...") 
    for key, metric_name in TARGET_METRICS.items():
        try:
            metric_data = prom_connection.get_current_metric_value(metric_name)
            if metric_data:
                latest_values[key] = float(metric_data[0]['value'][1])
            else:
                latest_values[key] = 0
        except Exception:
            latest_values[key] = 0
    return latest_values

def get_carbon_intensity() -> int:
    """Fetches the current carbon intensity from the UK National Grid API."""
    try:
        response = requests.get(CARBON_INTENSITY_API_URL)
        response.raise_for_status()
        data = response.json()
        actual_intensity = data['data'][0]['intensity']['actual']
        if actual_intensity is not None:
             print(f"  Successfully fetched Carbon Intensity: {actual_intensity} gCO2/kWh")
             return actual_intensity
        else:
             return data['data'][0]['intensity']['forecast']
    except Exception:
        return 0 

def estimate_power_watts(metrics: dict, previous_metrics: dict) -> float:
    """
    Estimates the current power consumption in Watts based on hardware assumptions.
    """

    # 'cpu_seconds_total' is a counter. The change over time gives us CPU-seconds used.
    cpu_seconds_used = metrics.get('cpu_seconds_total', 0) - previous_metrics.get('cpu_seconds_total', metrics.get('cpu_seconds_total', 0))
    # Dividing by the interval gives the average number of cores that were busy.
    average_cores_used = cpu_seconds_used / MONITORING_INTERVAL_SECONDS
    cpu_watts = average_cores_used * WATTS_PER_CORE

    # 'memory_active_bytes' is a gauge. We use its current value.
    memory_in_gb = metrics.get('memory_active_bytes', 0) / (1024 * 1024 * 1024)
    memory_watts = memory_in_gb * WATTS_PER_GB_MEM
    
    total_watts = IDLE_POWER_WATTS + cpu_watts + memory_watts
    return total_watts




if __name__ == "__main__":
    prom_client = connect_to_prometheus(PROMETHEUS_URL)
    
    if prom_client:
        previous_metrics_data = fetch_latest_metrics(prom_client)
        print("\n--- Starting Real-time Carbon Monitoring (press Ctrl+C to exit) ---\n")
        
        while True:
            try:
                time.sleep(MONITORING_INTERVAL_SECONDS)
                
                print(f"\n--- Timestamp: {time.ctime()} ---")
                
                current_metrics_data = fetch_latest_metrics(prom_client)
                carbon_intensity_gco2_kwh = get_carbon_intensity()

                if current_metrics_data and carbon_intensity_gco2_kwh > 0:

                    estimated_watts = estimate_power_watts(current_metrics_data, previous_metrics_data)
                    print(f"  - Estimated Power Draw: {estimated_watts:.2f} Watts")


                    interval_in_hours = MONITORING_INTERVAL_SECONDS / 3600
                    energy_kwh = (estimated_watts * interval_in_hours) / 1000
                    

                    grams_co2_eq = energy_kwh * carbon_intensity_gco2_kwh
                    print(f"  - Carbon Intensity: {carbon_intensity_gco2_kwh} gCO2/kWh")
                    print(f"  >>> Carbon Usage for last {MONITORING_INTERVAL_SECONDS}s: {grams_co2_eq:.4f} gCO2eq")

                    previous_metrics_data = current_metrics_data
                else:
                    print("  Could not retrieve all necessary data. Skipping calculation.")
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred in the main loop: {e}")
                time.sleep(MONITORING_INTERVAL_SECONDS)