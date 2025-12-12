"""
Unit tests for CarbonCalculator
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_calculation.CarbonCalculator import CarbonCalculator


class TestCarbonCalculator(unittest.TestCase):
    """Test cases for CarbonCalculator class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the Carbon Intensity API client
        self.mock_api_client = Mock()
        self.calculator = CarbonCalculator(self.mock_api_client)

    def test_initialization_with_client(self):
        """Test initialization with provided client."""
        calc = CarbonCalculator(self.mock_api_client)
        self.assertEqual(calc.api_client, self.mock_api_client)

    def test_initialization_without_client(self):
        """Test initialization without client creates default."""
        with patch('usage_calculation.CarbonCalculator.CarbonIntensityAPIClient'):
            calc = CarbonCalculator()
            self.assertIsNotNone(calc.api_client)

    def test_estimate_electricity_usage_kwh(self):
        """Test electricity usage calculation."""
        cpu_seconds = 7200  # 2 hours
        cpu_tdp = 65        # 65 Watts

        result = self.calculator.estimate_electricity_usage_kwh(cpu_seconds, cpu_tdp)

        # Expected: (7200 * 65) / (3600 * 1000) = 0.13
        expected = 0.13
        self.assertAlmostEqual(result, expected, places=9)

    def test_estimate_carbon_footprint_gCO2eq(self):
        """Test carbon footprint calculation with mocked intensity."""
        # Setup mock to return specific carbon intensity
        self.mock_api_client.get_carbon_intensity.return_value = 45.0

        cpu_seconds = 7200
        cpu_tdp = 65
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        result = self.calculator.estimate_carbon_footprint_gCO2eq(
            cpu_seconds, cpu_tdp, start_time
        )

        # Expected: 0.13 kWh * 45 g/kWh = 5.85 gCO2eq
        expected = 5.85
        self.assertAlmostEqual(result, expected, places=2)

        # Verify API was called with correct timestamp
        self.mock_api_client.get_carbon_intensity.assert_called_once_with(start_time)

    def test_estimate_carbon_footprint_zero_intensity(self):
        """Test with zero carbon intensity (API failure)."""
        self.mock_api_client.get_carbon_intensity.return_value = 0

        cpu_seconds = 7200
        cpu_tdp = 65
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        result = self.calculator.estimate_carbon_footprint_gCO2eq(
            cpu_seconds, cpu_tdp, start_time
        )

        self.assertEqual(result, 0.0)

    def test_estimate_carbon_footprint_detailed(self):
        """Test detailed carbon footprint with busy/idle."""
        self.mock_api_client.get_carbon_intensity.return_value = 45.0

        busy_seconds = 18000  # 5 hours
        idle_seconds = 54000  # 15 hours
        busy_power = 12
        idle_power = 1
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        result = self.calculator.estimate_carbon_footprint_detailed(
            busy_seconds, idle_seconds, busy_power, idle_power, start_time
        )

        # Check structure
        self.assertIn("electricity_kwh", result)
        self.assertIn("carbon_gco2eq", result)
        self.assertIn("carbon_intensity_g_per_kwh", result)
        self.assertIn("cpu_seconds", result)
        self.assertIn("power_w", result)

        # Check electricity values
        self.assertAlmostEqual(result["electricity_kwh"]["busy"], 0.06, places=5)
        self.assertAlmostEqual(result["electricity_kwh"]["idle"], 0.015, places=5)
        self.assertAlmostEqual(result["electricity_kwh"]["total"], 0.075, places=5)

        # Check carbon values (0.075 kWh * 45 g/kWh = 3.375 gCO2eq)
        expected_total_carbon = 3.375
        self.assertAlmostEqual(
            result["carbon_gco2eq"]["total"],
            expected_total_carbon,
            places=2
        )

        # Check intensity
        self.assertEqual(result["carbon_intensity_g_per_kwh"], 45.0)

        # Check CPU seconds
        self.assertEqual(result["cpu_seconds"]["busy"], busy_seconds)
        self.assertEqual(result["cpu_seconds"]["idle"], idle_seconds)
        self.assertEqual(result["cpu_seconds"]["total"], 72000)

        # Check power values
        self.assertEqual(result["power_w"]["busy"], busy_power)
        self.assertEqual(result["power_w"]["idle"], idle_power)

    def test_estimate_from_kwh(self):
        """Test direct kWh to carbon conversion."""
        self.mock_api_client.get_carbon_intensity.return_value = 50.0

        usage_kwh = 0.5
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        result = self.calculator.estimate_from_kwh(usage_kwh, start_time)

        # Expected: 0.5 kWh * 50 g/kWh = 25 gCO2eq
        expected = 25.0
        self.assertAlmostEqual(result, expected, places=2)

    def test_estimate_from_kwh_zero_intensity(self):
        """Test direct kWh conversion with zero intensity."""
        self.mock_api_client.get_carbon_intensity.return_value = 0

        usage_kwh = 0.5
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        result = self.calculator.estimate_from_kwh(usage_kwh, start_time)

        self.assertEqual(result, 0.0)


if __name__ == '__main__':
    unittest.main()
