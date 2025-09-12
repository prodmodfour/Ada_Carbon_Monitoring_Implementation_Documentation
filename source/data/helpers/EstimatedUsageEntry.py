import json


class EstimatedUsageEntry:
    def __init__(self):
        self.timestamp = None
        self.busy_cpu_seconds_total = None
        self.idle_cpu_seconds_total = None
        self.busy_usage_kwh = None
        self.idle_usage_kwh = None
        self.busy_usage_gCO2eq = None
        self.idle_usage_gCO2eq = None
        self.status = "not downloaded"

    def determine_status(self):
        has_cpu   = (self.busy_cpu_seconds_total is not None and
                    self.idle_cpu_seconds_total is not None)
        has_kwh   = (self.busy_usage_kwh is not None and
                    self.idle_usage_kwh is not None)
        has_co2   = (self.busy_usage_gCO2eq is not None and
                    self.idle_usage_gCO2eq is not None)
        has_usage = has_kwh and has_co2

        # Precedence: fake > not downloaded > unprocessed > processed
        if not has_cpu and has_usage:
            self.status = "fake"            # Data has been faked
        elif not has_cpu:
            self.status = "not downloaded"  # Data has not been downloaded
        elif not has_usage:
            self.status = "unprocessed"     # Data has been downloaded, but usage has not been computed
        else:
            self.status = "processed"


    def set_cpu_seconds_total(self, busy_cpu_seconds_total, idle_cpu_seconds_total):
        self.busy_cpu_seconds_total = busy_cpu_seconds_total
        self.idle_cpu_seconds_total = idle_cpu_seconds_total
        self.determine_status()

    def set_usage_kwh(self, busy_usage_kwh, idle_usage_kwh):
        self.busy_usage_kwh = busy_usage_kwh
        self.idle_usage_kwh = idle_usage_kwh
        self.determine_status()

    def set_usage_gCO2eq(self, busy_usage_gCO2eq, idle_usage_gCO2eq):
        self.busy_usage_gCO2eq = busy_usage_gCO2eq
        self.idle_usage_gCO2eq = idle_usage_gCO2eq
        self.determine_status()

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp
        self.determine_status()

    def construct_json(self):
        return json.dumps({
            "timestamp": self.timestamp,
            "busy_cpu_seconds_total": self.busy_cpu_seconds_total,
            "idle_cpu_seconds_total": self.idle_cpu_seconds_total,
            "busy_usage_kwh": self.busy_usage_kwh,
            "idle_usage_kwh": self.idle_usage_kwh,
            "busy_usage_gCO2eq": self.busy_usage_gCO2eq,
            "idle_usage_gCO2eq": self.idle_usage_gCO2eq,
            "status": self.status
        })
