class Machine:
    def __init__(self, name):
        self.name = name
        
        # CPU Seconds Total
        self.cpu_seconds_total = {
            "busy": {
                "number_data_points": 0,
                "running_average": 0,
            },
            "idle": {
                "number_data_points": 0,
                "running_average": 0,
            },   
        }
        # Energy KWh
        self.energy_kwh = {
            "busy": {
                "number_data_points": 0,
                "running_average": 0,
            },
            "idle": {
                "number_data_points": 0,
                "running_average": 0,
            },
        }
        # Carbon Footprint gCO2eq
        self.carbon_gCo2eq = {
            "busy": {
                "number_data_points": 0,
                "running_average": 0,
            },
            "idle": {
                "number_data_points": 0,
                "running_average": 0,
            },
        }
