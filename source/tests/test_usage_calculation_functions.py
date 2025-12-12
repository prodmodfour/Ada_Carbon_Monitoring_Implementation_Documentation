"""
Unit tests for legacy usage_calculation_functions
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_calculation.usage_calculation_functions import (
    estimate_electricity_usage_kwh,
    estimate_carbon_footprint_gCO2eq
)


class TestUsageCalculationFunctions(unittest.TestCase):
    """Test cases for legacy usage calculation functions."""

    def test_estimate_electricity_usage_kwh_basic(self):
        """Test basic electricity estimation."""
        # 7200 seconds (2 hours) * 65W = 468000 watt-seconds
        # 468000 / (3600 * 1000) = 0.13 kWh
        cpu_seconds = 7200.0
        cpu_tdp = 65.0

        result = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        expected = 0.13

        self.assertAlmostEqual(result, expected, places=5)

    def test_estimate_electricity_usage_kwh_one_hour(self):
        """Test electricity estimation for one hour."""
        # 3600 seconds * 100W = 360000 watt-seconds
        # 360000 / 3600000 = 0.1 kWh
        cpu_seconds = 3600.0
        cpu_tdp = 100.0

        result = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        expected = 0.1

        self.assertAlmostEqual(result, expected, places=10)

    def test_estimate_electricity_usage_kwh_zero_seconds(self):
        """Test electricity estimation with zero CPU seconds."""
        result = estimate_electricity_usage_kwh(0.0, 65.0)
        self.assertEqual(result, 0.0)

    def test_estimate_electricity_usage_kwh_zero_tdp(self):
        """Test electricity estimation with zero TDP."""
        result = estimate_electricity_usage_kwh(7200.0, 0.0)
        self.assertEqual(result, 0.0)

    def test_estimate_electricity_usage_kwh_high_values(self):
        """Test electricity estimation with high values."""
        # 86400 seconds (24 hours) * 250W
        # = 21600000 watt-seconds
        # = 6 kWh
        cpu_seconds = 86400.0
        cpu_tdp = 250.0

        result = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        expected = 6.0

        self.assertAlmostEqual(result, expected, places=5)

    def test_estimate_electricity_usage_kwh_fractional_values(self):
        """Test electricity estimation with fractional values."""
        cpu_seconds = 1800.0  # 30 minutes
        cpu_tdp = 45.5

        result = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        # 1800 * 45.5 / 3600000 = 0.02275 kWh
        expected = 0.02275

        self.assertAlmostEqual(result, expected, places=6)

    def test_estimate_carbon_footprint_gCO2eq_basic(self):
        """Test basic carbon footprint calculation."""
        usage_kwh = 0.13
        ci_g_per_kwh = 45.0

        result = estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh)
        expected = 5.85  # 0.13 * 45

        self.assertAlmostEqual(result, expected, places=5)

    def test_estimate_carbon_footprint_gCO2eq_zero_usage(self):
        """Test carbon footprint with zero usage."""
        result = estimate_carbon_footprint_gCO2eq(0.0, 45.0)
        self.assertEqual(result, 0.0)

    def test_estimate_carbon_footprint_gCO2eq_zero_intensity(self):
        """Test carbon footprint with zero carbon intensity."""
        result = estimate_carbon_footprint_gCO2eq(0.13, 0.0)
        self.assertEqual(result, 0.0)

    def test_estimate_carbon_footprint_gCO2eq_high_intensity(self):
        """Test carbon footprint with high carbon intensity."""
        usage_kwh = 1.0
        ci_g_per_kwh = 500.0  # High coal-based grid

        result = estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh)
        expected = 500.0

        self.assertAlmostEqual(result, expected, places=5)

    def test_estimate_carbon_footprint_gCO2eq_low_intensity(self):
        """Test carbon footprint with low carbon intensity."""
        usage_kwh = 1.0
        ci_g_per_kwh = 10.0  # Low renewable grid

        result = estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh)
        expected = 10.0

        self.assertAlmostEqual(result, expected, places=5)

    def test_estimate_carbon_footprint_gCO2eq_fractional_values(self):
        """Test carbon footprint with fractional values."""
        usage_kwh = 0.075
        ci_g_per_kwh = 33.7

        result = estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh)
        # 0.075 * 33.7 = 2.5275
        expected = 2.5275

        self.assertAlmostEqual(result, expected, places=6)

    def test_full_calculation_pipeline(self):
        """Test complete calculation from CPU seconds to carbon footprint."""
        # Step 1: Calculate kWh
        cpu_seconds = 7200.0
        cpu_tdp = 65.0
        kwh = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)

        # Step 2: Calculate carbon
        ci_g_per_kwh = 45.0
        carbon = estimate_carbon_footprint_gCO2eq(kwh, ci_g_per_kwh)

        # Verify
        expected_kwh = 0.13
        expected_carbon = 5.85

        self.assertAlmostEqual(kwh, expected_kwh, places=5)
        self.assertAlmostEqual(carbon, expected_carbon, places=5)

    def test_electricity_formula_correctness(self):
        """Verify the electricity formula: (seconds * watts) / (3600 * 1000)."""
        cpu_seconds = 3600.0
        cpu_tdp = 1000.0

        result = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)

        # Manual calculation:
        # watt_seconds = 3600 * 1000 = 3,600,000
        # kwh = 3,600,000 / 3,600,000 = 1.0
        expected = 1.0

        self.assertEqual(result, expected)

    def test_carbon_formula_correctness(self):
        """Verify the carbon formula: kwh * intensity."""
        usage_kwh = 2.5
        ci_g_per_kwh = 100.0

        result = estimate_carbon_footprint_gCO2eq(usage_kwh, ci_g_per_kwh)

        # Manual calculation: 2.5 * 100 = 250
        expected = 250.0

        self.assertEqual(result, expected)

    def test_very_small_values(self):
        """Test with very small values."""
        # 1 second of 1W CPU
        cpu_seconds = 1.0
        cpu_tdp = 1.0

        kwh = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        # 1 / 3,600,000 = 0.00000027778 kWh
        expected_kwh = 1.0 / (3600 * 1000)

        self.assertAlmostEqual(kwh, expected_kwh, places=12)

        # Calculate carbon
        carbon = estimate_carbon_footprint_gCO2eq(kwh, 45.0)
        expected_carbon = expected_kwh * 45.0

        self.assertAlmostEqual(carbon, expected_carbon, places=12)

    def test_negative_values_behavior(self):
        """Test behavior with negative values (edge case)."""
        # While negative values don't make physical sense,
        # the function should still compute them mathematically
        result_kwh = estimate_electricity_usage_kwh(-3600.0, 100.0)
        self.assertEqual(result_kwh, -0.1)

        result_carbon = estimate_carbon_footprint_gCO2eq(-0.1, 45.0)
        self.assertEqual(result_carbon, -4.5)

    def test_large_values(self):
        """Test with very large values."""
        # 1 year of operation
        cpu_seconds = 365 * 24 * 3600.0  # 31,536,000 seconds
        cpu_tdp = 100.0

        kwh = estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)
        # 31,536,000 * 100 / 3,600,000 = 876 kWh
        expected = 876.0

        self.assertAlmostEqual(kwh, expected, places=3)


if __name__ == '__main__':
    unittest.main()
