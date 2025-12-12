"""
Unit tests for EstimatedUsageEntry
"""
import unittest
import sys
import os
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.EstimatedUsageEntry import EstimatedUsageEntry


class TestEstimatedUsageEntry(unittest.TestCase):
    """Test cases for EstimatedUsageEntry class."""

    def setUp(self):
        """Set up test fixtures."""
        self.entry = EstimatedUsageEntry()

    def test_initialization(self):
        """Test entry initialization."""
        self.assertIsNone(self.entry.timestamp)
        self.assertIsNone(self.entry.busy_cpu_seconds_total)
        self.assertIsNone(self.entry.idle_cpu_seconds_total)
        self.assertIsNone(self.entry.busy_usage_kwh)
        self.assertIsNone(self.entry.idle_usage_kwh)
        self.assertIsNone(self.entry.busy_usage_gCO2eq)
        self.assertIsNone(self.entry.idle_usage_gCO2eq)
        self.assertEqual(self.entry.status, "not downloaded")

    def test_status_not_downloaded(self):
        """Test 'not downloaded' status."""
        # No data set
        self.entry.determine_status()
        self.assertEqual(self.entry.status, "not downloaded")

    def test_status_unprocessed(self):
        """Test 'unprocessed' status with CPU data only."""
        self.entry.set_cpu_seconds_total(100.0, 200.0)
        self.assertEqual(self.entry.status, "unprocessed")

    def test_status_processed(self):
        """Test 'processed' status with all data."""
        self.entry.set_cpu_seconds_total(100.0, 200.0)
        self.entry.set_usage_kwh(0.5, 0.2)
        self.entry.set_usage_gCO2eq(25.0, 10.0)
        self.assertEqual(self.entry.status, "processed")

    def test_status_fake(self):
        """Test 'fake' status with usage data but no CPU data."""
        # Set usage without CPU data
        self.entry.set_usage_kwh(0.5, 0.2)
        self.entry.set_usage_gCO2eq(25.0, 10.0)
        self.assertEqual(self.entry.status, "fake")

    def test_set_cpu_seconds_total(self):
        """Test setting CPU seconds."""
        self.entry.set_cpu_seconds_total(1000.0, 2000.0)
        self.assertEqual(self.entry.busy_cpu_seconds_total, 1000.0)
        self.assertEqual(self.entry.idle_cpu_seconds_total, 2000.0)
        self.assertEqual(self.entry.status, "unprocessed")

    def test_set_usage_kwh(self):
        """Test setting energy usage."""
        self.entry.set_usage_kwh(1.5, 0.8)
        self.assertEqual(self.entry.busy_usage_kwh, 1.5)
        self.assertEqual(self.entry.idle_usage_kwh, 0.8)

    def test_set_usage_gCO2eq(self):
        """Test setting carbon emissions."""
        self.entry.set_usage_gCO2eq(67.5, 36.0)
        self.assertEqual(self.entry.busy_usage_gCO2eq, 67.5)
        self.assertEqual(self.entry.idle_usage_gCO2eq, 36.0)

    def test_set_timestamp(self):
        """Test setting timestamp."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        self.entry.set_timestamp(timestamp)
        self.assertEqual(self.entry.timestamp, timestamp)

    def test_construct_json(self):
        """Test JSON construction."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        self.entry.set_timestamp(timestamp)
        self.entry.set_cpu_seconds_total(100.0, 200.0)
        self.entry.set_usage_kwh(0.5, 0.2)
        self.entry.set_usage_gCO2eq(25.0, 10.0)

        json_str = self.entry.construct_json()

        # Parse JSON
        data = json.loads(json_str)

        # Verify all fields
        self.assertEqual(data["timestamp"], timestamp.isoformat())
        self.assertEqual(data["busy_cpu_seconds_total"], 100.0)
        self.assertEqual(data["idle_cpu_seconds_total"], 200.0)
        self.assertEqual(data["busy_usage_kwh"], 0.5)
        self.assertEqual(data["idle_usage_kwh"], 0.2)
        self.assertEqual(data["busy_usage_gCO2eq"], 25.0)
        self.assertEqual(data["idle_usage_gCO2eq"], 10.0)
        self.assertEqual(data["status"], "processed")

    def test_status_precedence_fake_over_not_downloaded(self):
        """Test that 'fake' status takes precedence over 'not downloaded'."""
        # Only usage data, no CPU
        self.entry.set_usage_kwh(0.5, 0.2)
        self.assertEqual(self.entry.status, "not downloaded")

        # Add CO2 data - should become 'fake'
        self.entry.set_usage_gCO2eq(25.0, 10.0)
        self.assertEqual(self.entry.status, "fake")

    def test_status_update_on_each_setter(self):
        """Test that status updates after each setter call."""
        # Initial state
        self.assertEqual(self.entry.status, "not downloaded")

        # After CPU data
        self.entry.set_cpu_seconds_total(100.0, 200.0)
        self.assertEqual(self.entry.status, "unprocessed")

        # After kWh (still need CO2 for processed)
        self.entry.set_usage_kwh(0.5, 0.2)
        self.assertEqual(self.entry.status, "unprocessed")

        # After CO2
        self.entry.set_usage_gCO2eq(25.0, 10.0)
        self.assertEqual(self.entry.status, "processed")

    def test_zero_values(self):
        """Test with zero values."""
        self.entry.set_cpu_seconds_total(0.0, 0.0)
        self.entry.set_usage_kwh(0.0, 0.0)
        self.entry.set_usage_gCO2eq(0.0, 0.0)

        # Should still be 'processed' even with zeros
        self.assertEqual(self.entry.status, "processed")

    def test_partial_usage_data(self):
        """Test with only kWh or only CO2."""
        # Only kWh, no CO2 and no CPU
        self.entry.set_usage_kwh(0.5, 0.2)
        self.assertEqual(self.entry.status, "not downloaded")

        # Reset
        self.entry = EstimatedUsageEntry()

        # Only CO2, no kWh and no CPU
        self.entry.set_usage_gCO2eq(25.0, 10.0)
        self.assertEqual(self.entry.status, "not downloaded")

    def test_has_usage_logic(self):
        """Test the has_usage internal logic."""
        # has_usage requires both kWh AND CO2
        self.entry.set_usage_kwh(0.5, 0.2)
        # Only kWh is not enough for has_usage
        self.assertNotEqual(self.entry.status, "fake")

        self.entry.set_usage_gCO2eq(25.0, 10.0)
        # Now both are set, should be fake (no CPU)
        self.assertEqual(self.entry.status, "fake")

    def test_none_values_in_json(self):
        """Test JSON construction with None values."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        self.entry.set_timestamp(timestamp)

        json_str = self.entry.construct_json()
        data = json.loads(json_str)

        # None values should be null in JSON
        self.assertIsNone(data["busy_cpu_seconds_total"])
        self.assertIsNone(data["idle_cpu_seconds_total"])
        self.assertIsNone(data["busy_usage_kwh"])
        self.assertIsNone(data["idle_usage_kwh"])
        self.assertIsNone(data["busy_usage_gCO2eq"])
        self.assertIsNone(data["idle_usage_gCO2eq"])

    def test_mixed_none_and_zero(self):
        """Test behavior with mix of None and 0 values."""
        self.entry.set_cpu_seconds_total(0.0, 100.0)
        self.assertEqual(self.entry.busy_cpu_seconds_total, 0.0)
        self.assertEqual(self.entry.idle_cpu_seconds_total, 100.0)
        self.assertEqual(self.entry.status, "unprocessed")

    def test_timestamp_affects_status(self):
        """Test that timestamp doesn't affect status determination."""
        # Set timestamp first
        self.entry.set_timestamp(datetime.now())
        self.assertEqual(self.entry.status, "not downloaded")

        # Add CPU data
        self.entry.set_cpu_seconds_total(100.0, 200.0)
        self.assertEqual(self.entry.status, "unprocessed")

        # Status should still update correctly


if __name__ == '__main__':
    unittest.main()
