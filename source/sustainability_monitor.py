import time
import os
from prometheus_api_client import PrometheusConnect


PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "https://host-172-16-100-248.nubes.stfc.ac.uk")

TARGET_METRICS = {
    'cpu_seconds_total': 'node_cpu_seconds_total',
    'memory_active_bytes': 'node_memory_Active_bytes',
    'process_seconds_total': 'process_cpu_seconds_total',
    'go_routines': 'go_goroutines',

}

MODEL_WEIGHTS = {
    'cpu': 1.0,
    'memory': 1.0,
    'process': 1.0,
    'routines': 1.0,
}



def connect_to_prometheus(url: str):
    """
    Establishes a connection to the Prometheus server.
    Returns a PrometheusConnect object.
    """
    try:
        print(f"Connecting to Prometheus at {url}...")
        prom = PrometheusConnect(url=url, disable_ssl=True)
        if prom.check_prometheus_connection():
            print("Successfully connected to Prometheus.")
            return prom
        else:
            print("Connection check failed. Is Prometheus running and reachable?")
            return None
    except Exception as e:
        print(f"Error connecting to Prometheus: {e}")
        return None

def fetch_latest_metrics(prom_connection: PrometheusConnect) -> dict:
    """
    Fetches the latest value for each of our target metrics.
    Returns a dictionary of metric names and their current values.
    """
    latest_values = {}
    for key, metric_name in TARGET_METRICS.items():
        try:
            metric_data = prom_connection.get_current_metric_value(metric_name)
            if metric_data:
                value = float(metric_data[0]['value'][1])
                latest_values[key] = value
                print(f"  Successfully fetched {metric_name}: {value}")
            else:
                print(f"  Warning: Metric '{metric_name}' returned no data.")
                latest_values[key] = 0
        except Exception as e:
            print(f"  Error fetching metric '{metric_name}': {e}")
            latest_values[key] = 0
    return latest_values

def calculate_power_index(metrics: dict, previous_metrics: dict) -> float:
    """
    Calculates the 'Estimated Power Index' based on the fetched metrics.
    For counters (like cpu_seconds_total), we look at the rate of change.
    For gauges (like memory_active_bytes), we use a scaled version of the current value.
    """
    power_index = 0

    # Calculate CPU change (rate)
    cpu_change = metrics.get('cpu_seconds_total', 0) - previous_metrics.get('cpu_seconds_total', metrics.get('cpu_seconds_total', 0))
    power_index += MODEL_WEIGHTS['cpu'] * cpu_change

    # Calculate Process change (rate)
    process_change = metrics.get('process_seconds_total', 0) - previous_metrics.get('process_seconds_total', metrics.get('process_seconds_total', 0))
    power_index += MODEL_WEIGHTS['process'] * process_change
    
    # Add scaled memory usage (gauge). Convert bytes to Megabytes to normalize the value.
    memory_in_mb = metrics.get('memory_active_bytes', 0) / (1024 * 1024)
    power_index += MODEL_WEIGHTS['memory'] * memory_in_mb

    # Add go routines (gauge)
    power_index += MODEL_WEIGHTS['routines'] * metrics.get('go_routines', 0)
    
    return power_index



if __name__ == "__main__":
    prom_client = connect_to_prometheus(PROMETHEUS_URL)
    
    if prom_client:
        # Fetch initial set of metrics to establish a baseline
        previous_metrics_data = fetch_latest_metrics(prom_client)
        print("\n--- Starting Monitoring Loop (press Ctrl+C to exit) ---\n")
        
        while True:
            try:
                time.sleep(60) # Wait for 60 seconds
                
                print(f"\n--- Timestamp: {time.ctime()} ---")
                current_metrics_data = fetch_latest_metrics(prom_client)
                
                if current_metrics_data:
                    power_score = calculate_power_index(current_metrics_data, previous_metrics_data)
                    print(f"\n  >>> Calculated Power Index: {power_score:.2f}")
                    
                    # Update previous metrics for the next calculation
                    previous_metrics_data = current_metrics_data
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred in the main loop: {e}")
                time.sleep(60) # Wait before retrying