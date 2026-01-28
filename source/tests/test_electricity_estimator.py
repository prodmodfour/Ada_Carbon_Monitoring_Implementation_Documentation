"""
Unit tests for ElectricityEstimator
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_calculation.ElectricityEstimator import ElectricityEstimator


class TestElectricityEstimator(unittest.TestCase):
    """Test cases for ElectricityEstimator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.estimator = ElectricityEstimator(busy_power_w=12, idle_power_w=1)

    def test_initialization_default(self):
        """Test default initialization."""
        est = ElectricityEstimator()
        self.assertEqual(est.busy_power_w, 12.0)
        self.assertEqual(est.idle_power_w, 1.0)

    def test_initialization_custom(self):
        """Test custom initialization."""
        est = ElectricityEstimator(busy_power_w=15, idle_power_w=2)
        self.assertEqual(est.busy_power_w, 15.0)
        self.assertEqual(est.idle_power_w, 2.0)

    def test_estimate_usage_kwh_basic(self):
        """Test basic kWh estimation from specification example."""
        busy_seconds = 18000  # 5 hours
        idle_seconds = 54000  # 15 hours

        result = self.estimator.estimate_usage_kwh(busy_seconds, idle_seconds)

        # Expected: (12 * 18000 + 1 * 54000) / (3600 * 1000) = 0.075
        expected = 0.075
        self.assertAlmostEqual(result, expected, places=9)

    def test_estimate_usage_kwh_zero(self):
        """Test with zero CPU seconds."""
        result = self.estimator.estimate_usage_kwh(0, 0)
        self.assertEqual(result, 0.0)

    def test_estimate_usage_kwh_only_busy(self):
        """Test with only busy CPU time."""
        busy_seconds = 3600  # 1 hour
        idle_seconds = 0

        result = self.estimator.estimate_usage_kwh(busy_seconds, idle_seconds)

        # Expected: (12 * 3600) / (3600 * 1000) = 0.012
        expected = 0.012
        self.assertAlmostEqual(result, expected, places=9)

    def test_estimate_usage_kwh_only_idle(self):
        """Test with only idle CPU time."""
        busy_seconds = 0
        idle_seconds = 3600  # 1 hour

        result = self.estimator.estimate_usage_kwh(busy_seconds, idle_seconds)

        # Expected: (1 * 3600) / (3600 * 1000) = 0.001
        expected = 0.001
        self.assertAlmostEqual(result, expected, places=9)

    def test_estimate_busy_usage_kwh(self):
        """Test separate busy usage calculation."""
        busy_seconds = 7200  # 2 hours

        result = self.estimator.estimate_busy_usage_kwh(busy_seconds)

        # Expected: (12 * 7200) / (3600 * 1000) = 0.024
        expected = 0.024
        self.assertAlmostEqual(result, expected, places=9)

    def test_estimate_idle_usage_kwh(self):
        """Test separate idle usage calculation."""
        idle_seconds = 7200  # 2 hours

        result = self.estimator.estimate_idle_usage_kwh(idle_seconds)

        # Expected: (1 * 7200) / (3600 * 1000) = 0.002
        expected = 0.002
        self.assertAlmostEqual(result, expected, places=9)

    def test_get_power_consumption_breakdown(self):
        """Test detailed breakdown functionality."""
        busy_seconds = 18000
        idle_seconds = 54000

        breakdown = self.estimator.get_power_consumption_breakdown(
            busy_seconds, idle_seconds
        )

        # Check structure
        self.assertIn("busy", breakdown)
        self.assertIn("idle", breakdown)
        self.assertIn("total", breakdown)

        # Check busy values
        self.assertEqual(breakdown["busy"]["cpu_seconds"], busy_seconds)
        self.assertEqual(breakdown["busy"]["power_w"], 12)
        self.assertAlmostEqual(breakdown["busy"]["usage_kwh"], 0.06, places=9)
        self.assertAlmostEqual(breakdown["busy"]["percentage"], 25.0, places=1)

        # Check idle values
        self.assertEqual(breakdown["idle"]["cpu_seconds"], idle_seconds)
        self.assertEqual(breakdown["idle"]["power_w"], 1)
        self.assertAlmostEqual(breakdown["idle"]["usage_kwh"], 0.015, places=9)
        self.assertAlmostEqual(breakdown["idle"]["percentage"], 75.0, places=1)

        # Check total
        self.assertEqual(breakdown["total"]["cpu_seconds"], 72000)
        self.assertAlmostEqual(breakdown["total"]["usage_kwh"], 0.075, places=9)

    def test_breakdown_zero_division(self):
        """Test breakdown with zero total seconds."""
        breakdown = self.estimator.get_power_consumption_breakdown(0, 0)

        self.assertEqual(breakdown["busy"]["percentage"], 0)
        self.assertEqual(breakdown["idle"]["percentage"], 0)

    def test_different_power_constants(self):
        """Test with different power constants."""
        est = ElectricityEstimator(busy_power_w=20, idle_power_w=5)

        result = est.estimate_usage_kwh(3600, 3600)

        # Expected: (20 * 3600 + 5 * 3600) / (3600 * 1000) = 0.025
        expected = 0.025
        self.assertAlmostEqual(result, expected, places=9)


if __name__ == '__main__':
    unittest.main()
