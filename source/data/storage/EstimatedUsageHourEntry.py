import typing

class EstimatedUsageHourEntry:

    def __init__(self, hour: str):
        self.hour = hour

        self.data = dict()
    
    def compute_all_entry(self):
        cumulative_busy_cpu_seconds_total = 0
        cumulative_idle_cpu_seconds_total = 0
        cumulative_busy_kwh = 0
        cumulative_idle_kwh = 0
        cumulative_busy_gCo2eq = 0
        cumulative_idle_gCo2eq = 0

        for key,values in self.data.items():
            if key == "all":
                continue

            cumulative_busy_cpu_seconds_total += values["busy_cpu_seconds_total"]
            cumulative_idle_cpu_seconds_total += values["idle_cpu_seconds_total"]
            cumulative_busy_kwh += values["busy_kwh"]
            cumulative_idle_kwh += values["idle_kwh"]
            cumulative_busy_gCo2eq += values["busy_gCo2eq"]
            cumulative_idle_gCo2eq += values["idle_gCo2eq"]
            
        self.data["all"] = {
            "busy_cpu_seconds_total": cumulative_busy_cpu_seconds_total,
            "idle_cpu_seconds_total": cumulative_idle_cpu_seconds_total,
            "busy_kwh": cumulative_busy_kwh,
            "idle_kwh": cumulative_idle_kwh,
            "busy_gCo2eq": cumulative_busy_gCo2eq,
            "idle_gCo2eq": cumulative_idle_gCo2eq
        }
    
    def add_entry(self, machine_name: str, busy_cpu_seconds_total: float, idle_cpu_seconds_total: float, busy_kwh: float, idle_kwh: float, busy_gCo2eq: float, idle_gCo2eq: float):
        self.data[machine_name] = {
            "busy_cpu_seconds_total": busy_cpu_seconds_total,
            "idle_cpu_seconds_total": idle_cpu_seconds_total,
            "busy_kwh": busy_kwh,
            "idle_kwh": idle_kwh,
            "busy_gCo2eq": busy_gCo2eq,
            "idle_gCo2eq": idle_gCo2eq
        }


