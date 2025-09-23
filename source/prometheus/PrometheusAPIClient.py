import requests

class PrometheusAPIClient:
    def __init__(self, prometheus_url = "https://host-172-16-100-248.nubes.stfc.ac.uk/", api_endpoint = "api/v1/query_range", timeout=120):
        if not prometheus_url.endswith("/"):
            prometheus_url = prometheus_url + "/"
        
        if api_endpoint.startswith("/"):
            api_endpoint = api_endpoint[1:]

        self.base_url = prometheus_url
        self.api_endpoint = api_endpoint
        self.url = self.base_url + self.api_endpoint
        self.timeout = timeout

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
            print(f"Request timed out for entry at {parameters.get("start")}. Skipping.")

            return None
        except requests.HTTPError as e:
            try:
                print("Error body:", response.text)
            except Exception:
                pass
        except Exception:
            pass
            print(f"HTTPError for entry at {parameters.get("start")}. Skipping.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"RequestException for entry at {parameters.get("start")}. Skipping.")
            return None
        return None

