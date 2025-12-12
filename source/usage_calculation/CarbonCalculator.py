"""
Carbon Calculator
Integrates electricity estimation with Carbon Intensity API to calculate carbon footprint.
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_calculation.CarbonIntensityAPIClient import CarbonIntensityAPIClient


class CarbonCalculator:
    """
    Calculates carbon footprint by combining electricity usage with carbon intensity data.

    This class provides both TDP-based and detailed busy/idle estimation methods,
    integrating with the Carbon Intensity API to get real-time grid intensity data.
    """

    def __init__(self, api_client: Optional[CarbonIntensityAPIClient] = None):
        """
        Initialize the Carbon Calculator.

        Args:
            api_client: Instance of CarbonIntensityAPIClient to fetch grid intensity.
                       If None, creates a new instance.
        """
        self.api_client = api_client if api_client else CarbonIntensityAPIClient()

    def estimate_electricity_usage_kwh(
        self,
        cpu_seconds_total: float,
        cpu_tdp_w: float
    ) -> float:
        """
        Calculates electricity usage in kWh based on TDP and total time.

        Formula: usage_kwh = (seconds * tdp) / (3600 * 1000)

        Args:
            cpu_seconds_total: Total CPU seconds (busy + idle).
            cpu_tdp_w: CPU Thermal Design Power in Watts.

        Returns:
            float: Estimated electricity usage in kWh.
        """
        usage_kwh = (cpu_seconds_total * cpu_tdp_w) / (3600 * 1000)
        return usage_kwh

    def estimate_carbon_footprint_gCO2eq(
        self,
        cpu_seconds_total: float,
        cpu_tdp_w: float,
        start_time: datetime
    ) -> float:
        """
        Calculates carbon footprint in grams (gCO2e) using TDP method.

        Steps:
        1. Estimates kWh usage using TDP.
        2. Fetches carbon intensity for the hour starting at start_time.
        3. Multiplies kWh by intensity.

        Args:
            cpu_seconds_total: Total CPU seconds.
            cpu_tdp_w: CPU TDP in Watts.
            start_time: Start time for carbon intensity lookup.

        Returns:
            float: Carbon footprint in grams CO2 equivalent.
        """
        # 1. Estimate Energy
        usage_kwh = self.estimate_electricity_usage_kwh(cpu_seconds_total, cpu_tdp_w)

        # 2. Fetch Intensity
        intensity_g_per_kwh = self.api_client.get_carbon_intensity(start_time)

        if intensity_g_per_kwh == 0:
            print("Warning: Carbon intensity returned 0 (API failure or missing data). Footprint will be 0.")

        # 3. Calculate Footprint
        carbon_footprint_g = usage_kwh * intensity_g_per_kwh

        return carbon_footprint_g

    def estimate_carbon_footprint_detailed(
        self,
        busy_cpu_seconds: float,
        idle_cpu_seconds: float,
        busy_power_w: float,
        idle_power_w: float,
        start_time: datetime
    ) -> dict:
        """
        Calculates detailed carbon footprint with separate busy/idle calculations.

        Args:
            busy_cpu_seconds: CPU seconds in busy state.
            idle_cpu_seconds: CPU seconds in idle state.
            busy_power_w: Power consumption when busy (Watts).
            idle_power_w: Power consumption when idle (Watts).
            start_time: Start time for carbon intensity lookup.

        Returns:
            dict: Detailed breakdown with busy, idle, and total metrics.
        """
        # Calculate electricity usage
        busy_kwh = (busy_power_w * busy_cpu_seconds) / (3600 * 1000)
        idle_kwh = (idle_power_w * idle_cpu_seconds) / (3600 * 1000)
        total_kwh = busy_kwh + idle_kwh

        # Get carbon intensity
        intensity_g_per_kwh = self.api_client.get_carbon_intensity(start_time)

        if intensity_g_per_kwh == 0:
            print("Warning: Carbon intensity returned 0. Carbon footprint will be 0.")

        # Calculate carbon footprint
        busy_gco2eq = busy_kwh * intensity_g_per_kwh
        idle_gco2eq = idle_kwh * intensity_g_per_kwh
        total_gco2eq = busy_gco2eq + idle_gco2eq

        return {
            "electricity_kwh": {
                "busy": busy_kwh,
                "idle": idle_kwh,
                "total": total_kwh
            },
            "carbon_gco2eq": {
                "busy": busy_gco2eq,
                "idle": idle_gco2eq,
                "total": total_gco2eq
            },
            "carbon_intensity_g_per_kwh": intensity_g_per_kwh,
            "cpu_seconds": {
                "busy": busy_cpu_seconds,
                "idle": idle_cpu_seconds,
                "total": busy_cpu_seconds + idle_cpu_seconds
            },
            "power_w": {
                "busy": busy_power_w,
                "idle": idle_power_w
            }
        }

    def estimate_from_kwh(
        self,
        usage_kwh: float,
        start_time: datetime
    ) -> float:
        """
        Calculate carbon footprint directly from kWh usage.

        Args:
            usage_kwh: Electricity usage in kWh.
            start_time: Start time for carbon intensity lookup.

        Returns:
            float: Carbon footprint in grams CO2 equivalent.
        """
        intensity_g_per_kwh = self.api_client.get_carbon_intensity(start_time)

        if intensity_g_per_kwh == 0:
            print("Warning: Carbon intensity returned 0. Carbon footprint will be 0.")

        return usage_kwh * intensity_g_per_kwh


# --- Example Usage ---
if __name__ == "__main__":
    print("=== Carbon Calculator Example ===\n")

    # Setup
    client = CarbonIntensityAPIClient()
    calculator = CarbonCalculator(client)

    # Inputs from worked example
    cpu_sec = 7200      # 7,200 seconds
    tdp = 65            # 65 Watts

    # Use a recent past time (yesterday noon) to ensure the API has 'actual' data
    query_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(days=1)

    print(f"Calculating for: {query_time} UTC\n")

    # Execute TDP-based calculation
    print("=== TDP-Based Calculation ===")
    footprint = calculator.estimate_carbon_footprint_gCO2eq(cpu_sec, tdp, query_time)

    # Output details
    usage = calculator.estimate_electricity_usage_kwh(cpu_sec, tdp)
    print(f"CPU Seconds:     {cpu_sec}")
    print(f"CPU TDP:         {tdp} W")
    print(f"Energy Usage:    {usage:.5f} kWh")
    print(f"Total Footprint: {footprint:.2f} gCO2e\n")

    # Execute detailed calculation with busy/idle
    print("=== Detailed Busy/Idle Calculation ===")
    busy_sec = 18000  # 5 hours
    idle_sec = 54000  # 15 hours
    busy_power = 12   # 12W when busy
    idle_power = 1    # 1W when idle

    detailed = calculator.estimate_carbon_footprint_detailed(
        busy_cpu_seconds=busy_sec,
        idle_cpu_seconds=idle_sec,
        busy_power_w=busy_power,
        idle_power_w=idle_power,
        start_time=query_time
    )

    print(f"Busy CPU: {detailed['cpu_seconds']['busy']} seconds")
    print(f"Idle CPU: {detailed['cpu_seconds']['idle']} seconds")
    print(f"Total CPU: {detailed['cpu_seconds']['total']} seconds\n")

    print(f"Busy Energy: {detailed['electricity_kwh']['busy']:.5f} kWh")
    print(f"Idle Energy: {detailed['electricity_kwh']['idle']:.5f} kWh")
    print(f"Total Energy: {detailed['electricity_kwh']['total']:.5f} kWh\n")

    print(f"Carbon Intensity: {detailed['carbon_intensity_g_per_kwh']:.2f} g/kWh\n")

    print(f"Busy Carbon: {detailed['carbon_gco2eq']['busy']:.2f} gCO2e")
    print(f"Idle Carbon: {detailed['carbon_gco2eq']['idle']:.2f} gCO2e")
    print(f"Total Carbon: {detailed['carbon_gco2eq']['total']:.2f} gCO2e\n")

    # Calculate from kWh directly
    print("=== Direct kWh Calculation ===")
    kwh = 0.5
    carbon_from_kwh = calculator.estimate_from_kwh(kwh, query_time)
    print(f"Energy: {kwh} kWh")
    print(f"Carbon: {carbon_from_kwh:.2f} gCO2e")
