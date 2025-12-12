
import requests
from datetime import datetime, timezone

class PrometheusAPIClient:
    def __init__(self, prometheus_url="https://host-172-16-100-248.nubes.stfc.ac.uk/", api_endpoint="api/v1/query_range", timeout=120):
        if not prometheus_url.endswith("/"):
            prometheus_url = prometheus_url + "/"
        
        if api_endpoint.startswith("/"):
            api_endpoint = api_endpoint[1:]

        self.base_url = prometheus_url
        self.api_endpoint = api_endpoint
        self.url = self.base_url + self.api_endpoint
        self.timeout = timeout

    def _to_rfc3339(self, date: datetime) -> str:
        """Helper to format datetime to RFC3339 string."""
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        else:
            date = date.astimezone(timezone.utc)
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

    def query(self, parameters):
        try:
            # Make the request
            response = requests.get(self.url, params=parameters, timeout=self.timeout)

            print("URL:", response.url)
            print("Status:", response.status_code, response.reason)
            response.raise_for_status()  # raises on 4xx/5xx
            print("OK → proceeding to parse JSON")
            data = response.json()
            print("Prometheus status:", data.get("status"))
            return data

        except requests.exceptions.ReadTimeout:
            # Fixed f-string quote syntax error
            print(f"Request timed out for entry at {parameters.get('start')}. Skipping.")
            return None

        except requests.exceptions.HTTPError as e:
            try:
                print("Error body:", response.text)
            except Exception:
                pass
            # Fixed f-string quote syntax error
            print(f"HTTPError for entry at {parameters.get('start')}. Skipping.")
            return None

        except requests.exceptions.RequestException as e:
            # Fixed f-string quote syntax error
            print(f"RequestException for entry at {parameters.get('start')}. Skipping.")
            return None
        
        except Exception as e:
             print(f"An unexpected error occurred: {e}")
             return None

    def cpu_seconds_total(self, timestamp: datetime, cloud_project_name: str, machine_name: str = None, host: str = None, step: str = '1h'):
        """
        Calculates the increase in cpu seconds.
        Supports filtering by cloud_project_name, machine_name, and host.
        """
        # Build the selector string based on provided arguments
        selectors = [f'cloud_project_name="{cloud_project_name}"']
        
        if machine_name:
            selectors.append(f'machine_name="{machine_name}"')
        
        if host:
            selectors.append(f'host="{host}"')
            
        selector_str = ",".join(selectors)
        
        # Construct the PromQL query
        query = f'increase(node_cpu_seconds_total{{{selector_str}}}[{step}])'

        parameters = {
            "query": query,
            "start": self._to_rfc3339(timestamp),
            "end": self._to_rfc3339(timestamp),
            "step": step
        }

        return self.query(parameters)

# Example Usage
if __name__ == "__main__":
    client = PrometheusAPIClient()
    
    # Example call with new parameters
    result = client.cpu_seconds_total(
        timestamp=datetime.now(), 
        cloud_project_name="CDAaaS",
    )
    print(result)