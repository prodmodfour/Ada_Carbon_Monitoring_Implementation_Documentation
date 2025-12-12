"""
Electricity Estimator
Estimates electricity usage (in kWh) based on CPU busy and idle times with different power constants.
"""


class ElectricityEstimator:
    """
    Estimates electricity usage (in kWh) based on CPU busy and idle times.

    This approach uses separate power consumption values for busy and idle CPU states,
    providing more accurate estimates than simple TDP-based calculations.

    Attributes:
        busy_power_w (float): Power consumption of a busy CPU core in Watts.
        idle_power_w (float): Power consumption of an idle CPU core in Watts.
    """

    def __init__(self, busy_power_w: float = 12.0, idle_power_w: float = 1.0):
        """
        Initializes the estimator with specific power constants.

        Args:
            busy_power_w (float): Watts used when the CPU is busy. Default is 12 W.
            idle_power_w (float): Watts used when the CPU is idle. Default is 1 W.
        """
        self.busy_power_w = busy_power_w
        self.idle_power_w = idle_power_w

    def estimate_usage_kwh(self, busy_cpu_seconds: float, idle_cpu_seconds: float) -> float:
        """
        Calculates the estimated electricity usage in kWh.

        Formula:
            (busy_watts * busy_seconds + idle_watts * idle_seconds) / (3600 * 1000)

        Args:
            busy_cpu_seconds (float): Total CPU-seconds spent in the 'busy' state.
            idle_cpu_seconds (float): Total CPU-seconds spent in the 'idle' state.

        Returns:
            float: Estimated energy consumption in kilowatt-hours (kWh).
        """
        # Calculate total energy in Watt-seconds (Joules)
        total_watt_seconds = (self.busy_power_w * busy_cpu_seconds) + \
                             (self.idle_power_w * idle_cpu_seconds)

        # Convert Watt-seconds to kWh (divide by 3,600,000)
        # 1 hour = 3600 seconds
        # 1 kW = 1000 Watts
        kwh_usage = total_watt_seconds / (3600 * 1000)

        return kwh_usage

    def estimate_busy_usage_kwh(self, busy_cpu_seconds: float) -> float:
        """
        Calculates electricity usage for busy CPU time only.

        Args:
            busy_cpu_seconds (float): Total CPU-seconds spent in the 'busy' state.

        Returns:
            float: Estimated busy energy consumption in kWh.
        """
        return (self.busy_power_w * busy_cpu_seconds) / (3600 * 1000)

    def estimate_idle_usage_kwh(self, idle_cpu_seconds: float) -> float:
        """
        Calculates electricity usage for idle CPU time only.

        Args:
            idle_cpu_seconds (float): Total CPU-seconds spent in the 'idle' state.

        Returns:
            float: Estimated idle energy consumption in kWh.
        """
        return (self.idle_power_w * idle_cpu_seconds) / (3600 * 1000)

    def get_power_consumption_breakdown(
        self,
        busy_cpu_seconds: float,
        idle_cpu_seconds: float
    ) -> dict:
        """
        Get a detailed breakdown of power consumption.

        Args:
            busy_cpu_seconds (float): Total CPU-seconds in busy state.
            idle_cpu_seconds (float): Total CPU-seconds in idle state.

        Returns:
            dict: Breakdown with busy, idle, and total usage.
        """
        busy_kwh = self.estimate_busy_usage_kwh(busy_cpu_seconds)
        idle_kwh = self.estimate_idle_usage_kwh(idle_cpu_seconds)
        total_kwh = busy_kwh + idle_kwh

        total_seconds = busy_cpu_seconds + idle_cpu_seconds
        busy_percentage = (busy_cpu_seconds / total_seconds * 100) if total_seconds > 0 else 0
        idle_percentage = (idle_cpu_seconds / total_seconds * 100) if total_seconds > 0 else 0

        return {
            "busy": {
                "cpu_seconds": busy_cpu_seconds,
                "power_w": self.busy_power_w,
                "usage_kwh": busy_kwh,
                "percentage": busy_percentage
            },
            "idle": {
                "cpu_seconds": idle_cpu_seconds,
                "power_w": self.idle_power_w,
                "usage_kwh": idle_kwh,
                "percentage": idle_percentage
            },
            "total": {
                "cpu_seconds": total_seconds,
                "usage_kwh": total_kwh
            }
        }


# --- Example Usage ---
if __name__ == "__main__":
    print("=== Electricity Estimator Example ===\n")

    # 1. Initialize the estimator with the assumptions: Busy=12W, Idle=1W
    estimator = ElectricityEstimator(busy_power_w=12, idle_power_w=1)

    # 2. Define the inputs from the example
    busy_seconds = 18000
    idle_seconds = 54000

    # 3. Calculate usage
    result_kwh = estimator.estimate_usage_kwh(busy_seconds, idle_seconds)

    # 4. Display results
    print(f"Inputs:")
    print(f"  Busy CPU Seconds: {busy_seconds}")
    print(f"  Idle CPU Seconds: {idle_seconds}")
    print(f"  Busy Power:       {estimator.busy_power_w} W")
    print(f"  Idle Power:       {estimator.idle_power_w} W")
    print("-" * 40)
    print(f"Estimated Energy:   {result_kwh:.5f} kWh")

    # Verification check against the provided example result
    assert abs(result_kwh - 0.075) < 1e-9, "Calculation did not match the example!"
    print("✓ Verification passed: Result matches 0.075 kWh.\n")

    # 5. Get detailed breakdown
    print("=== Detailed Breakdown ===")
    breakdown = estimator.get_power_consumption_breakdown(busy_seconds, idle_seconds)

    print(f"\nBusy State:")
    print(f"  CPU Seconds: {breakdown['busy']['cpu_seconds']}")
    print(f"  Power: {breakdown['busy']['power_w']} W")
    print(f"  Usage: {breakdown['busy']['usage_kwh']:.5f} kWh")
    print(f"  Percentage: {breakdown['busy']['percentage']:.1f}%")

    print(f"\nIdle State:")
    print(f"  CPU Seconds: {breakdown['idle']['cpu_seconds']}")
    print(f"  Power: {breakdown['idle']['power_w']} W")
    print(f"  Usage: {breakdown['idle']['usage_kwh']:.5f} kWh")
    print(f"  Percentage: {breakdown['idle']['percentage']:.1f}%")

    print(f"\nTotal:")
    print(f"  CPU Seconds: {breakdown['total']['cpu_seconds']}")
    print(f"  Usage: {breakdown['total']['usage_kwh']:.5f} kWh")
