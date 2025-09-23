class CarbonIntensityAPIClient:
    def __init__(self):
        self.api_url = "https://api.carbonintensity.org.uk/intensity"

    def get_carbon_intensity(self, start_time, end_time):
        url = self.api_url + "/" + start_time + "/" + end_time
        response = requests.get(url)
        return response.json()