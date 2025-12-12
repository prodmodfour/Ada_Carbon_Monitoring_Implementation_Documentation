"""
Unit tests for WorkspaceUsageEntry
"""
import unittest
import sys
import os
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workspace_tracking.WorkspaceUsageEntry import WorkspaceUsageEntry


class TestWorkspaceUsageEntry(unittest.TestCase):
    """Test cases for WorkspaceUsageEntry class."""

    def setUp(self):
        """Set up test fixtures."""
        self.entry = WorkspaceUsageEntry(
            workspace_id="507f1f77bcf86cd799439011",
            hostname="172.16.100.50",
            owner="john.doe"
        )

    def test_initialization(self):
        """Test entry initialization."""
        self.assertEqual(self.entry.workspace_id, "507f1f77bcf86cd799439011")
        self.assertEqual(self.entry.hostname, "172.16.100.50")
        self.assertEqual(self.entry.owner, "john.doe")
        self.assertIsNone(self.entry.timestamp)
        self.assertEqual(self.entry.status, "initialized")

    def test_status_progression_initialized(self):
        """Test status remains initialized with no data."""
        self.assertEqual(self.entry.status, "initialized")

    def test_status_progression_downloaded(self):
        """Test status becomes downloaded with CPU data."""
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.assertEqual(self.entry.status, "downloaded")

    def test_status_progression_processed(self):
        """Test status becomes processed with CPU, energy, and carbon data."""
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.entry.set_usage_kwh(2.5, 1.0)
        self.entry.set_usage_gco2eq(112.5, 45.0)
        self.assertEqual(self.entry.status, "processed")

    def test_status_progression_complete(self):
        """Test status becomes complete with all data."""
        self.entry.set_timestamp(datetime(2025, 1, 15, 12, 0, 0))
        self.entry.set_user_info({
            "platform_name": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com"
        })
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.entry.set_usage_kwh(2.5, 1.0)
        self.entry.set_usage_gco2eq(112.5, 45.0)
        self.assertEqual(self.entry.status, "complete")

    def test_set_timestamp(self):
        """Test setting timestamp."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        self.entry.set_timestamp(timestamp)
        self.assertEqual(self.entry.timestamp, timestamp)

    def test_set_user_info(self):
        """Test setting user information."""
        user_info = {
            "platform_name": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "uid": 1001
        }
        self.entry.set_user_info(user_info)
        self.assertEqual(self.entry.user_info, user_info)

    def test_set_cpu_seconds_total(self):
        """Test setting CPU seconds."""
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.assertEqual(self.entry.busy_cpu_seconds_total, 3600.0)
        self.assertEqual(self.entry.idle_cpu_seconds_total, 1800.0)

    def test_set_usage_kwh(self):
        """Test setting energy usage."""
        self.entry.set_usage_kwh(2.5, 1.0)
        self.assertEqual(self.entry.busy_usage_kwh, 2.5)
        self.assertEqual(self.entry.idle_usage_kwh, 1.0)
        self.assertEqual(self.entry.total_usage_kwh, 3.5)

    def test_set_usage_gco2eq(self):
        """Test setting carbon emissions."""
        self.entry.set_usage_gco2eq(112.5, 45.0, carbon_intensity=45.0)
        self.assertEqual(self.entry.busy_usage_gco2eq, 112.5)
        self.assertEqual(self.entry.idle_usage_gco2eq, 45.0)
        self.assertEqual(self.entry.total_usage_gco2eq, 157.5)
        self.assertEqual(self.entry.carbon_intensity_g_per_kwh, 45.0)

    def test_set_usage_gco2eq_without_intensity(self):
        """Test setting carbon emissions without intensity."""
        self.entry.set_usage_gco2eq(112.5, 45.0)
        self.assertEqual(self.entry.busy_usage_gco2eq, 112.5)
        self.assertEqual(self.entry.idle_usage_gco2eq, 45.0)
        self.assertIsNone(self.entry.carbon_intensity_g_per_kwh)

    def test_set_carbon_equivalencies(self):
        """Test setting carbon equivalencies."""
        equivalencies = {
            "smartphone_charges": 19.15,
            "miles_driven": 0.39
        }
        self.entry.set_carbon_equivalencies(equivalencies)
        self.assertEqual(self.entry.carbon_equivalencies, equivalencies)

    def test_set_cpu_tdp(self):
        """Test setting CPU TDP."""
        self.entry.set_cpu_tdp(65.0)
        self.assertEqual(self.entry.cpu_tdp_w, 65.0)

    def test_to_dict_basic(self):
        """Test dictionary conversion with basic data."""
        result = self.entry.to_dict()

        self.assertEqual(result["workspace_id"], "507f1f77bcf86cd799439011")
        self.assertEqual(result["hostname"], "172.16.100.50")
        self.assertEqual(result["owner"], "john.doe")
        self.assertEqual(result["status"], "initialized")

    def test_to_dict_complete(self):
        """Test dictionary conversion with complete data."""
        # Set all data
        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        self.entry.set_timestamp(timestamp)
        self.entry.set_user_info({"platform_name": "john.doe"})
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.entry.set_usage_kwh(2.5, 1.0)
        self.entry.set_usage_gco2eq(112.5, 45.0, carbon_intensity=45.0)
        self.entry.set_carbon_equivalencies({"miles_driven": 0.39})
        self.entry.set_cpu_tdp(65.0)

        result = self.entry.to_dict()

        # Verify all fields
        self.assertEqual(result["timestamp"], timestamp.isoformat())
        self.assertEqual(result["user_info"]["platform_name"], "john.doe")
        self.assertEqual(result["cpu_usage"]["busy_seconds"], 3600.0)
        self.assertEqual(result["cpu_usage"]["idle_seconds"], 1800.0)
        self.assertEqual(result["cpu_usage"]["total_seconds"], 5400.0)
        self.assertEqual(result["energy_kwh"]["busy"], 2.5)
        self.assertEqual(result["energy_kwh"]["idle"], 1.0)
        self.assertEqual(result["energy_kwh"]["total"], 3.5)
        self.assertEqual(result["carbon_gco2eq"]["busy"], 112.5)
        self.assertEqual(result["carbon_gco2eq"]["idle"], 45.0)
        self.assertEqual(result["carbon_gco2eq"]["total"], 157.5)
        self.assertEqual(result["carbon_intensity_g_per_kwh"], 45.0)
        self.assertEqual(result["carbon_equivalencies"]["miles_driven"], 0.39)
        self.assertEqual(result["cpu_tdp_w"], 65.0)
        self.assertEqual(result["status"], "complete")

    def test_to_json(self):
        """Test JSON conversion."""
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        json_str = self.entry.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["workspace_id"], "507f1f77bcf86cd799439011")
        self.assertEqual(parsed["cpu_usage"]["busy_seconds"], 3600.0)

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.entry)

        self.assertIn("WorkspaceUsageEntry", repr_str)
        self.assertIn("507f1f77bcf86cd799439011", repr_str)
        self.assertIn("172.16.100.50", repr_str)
        self.assertIn("john.doe", repr_str)
        self.assertIn("initialized", repr_str)

    def test_total_cpu_calculation_none(self):
        """Test total CPU calculation with None values."""
        result = self.entry.to_dict()
        self.assertIsNone(result["cpu_usage"]["total_seconds"])

    def test_total_cpu_calculation_with_values(self):
        """Test total CPU calculation with actual values."""
        self.entry.set_cpu_seconds_total(1000.0, 2000.0)
        result = self.entry.to_dict()
        self.assertEqual(result["cpu_usage"]["total_seconds"], 3000.0)

    def test_zero_values(self):
        """Test with zero values."""
        self.entry.set_cpu_seconds_total(0.0, 0.0)
        self.entry.set_usage_kwh(0.0, 0.0)
        self.entry.set_usage_gco2eq(0.0, 0.0)

        self.assertEqual(self.entry.status, "processed")
        self.assertEqual(self.entry.total_usage_kwh, 0.0)
        self.assertEqual(self.entry.total_usage_gco2eq, 0.0)

    def test_status_update_partial_data(self):
        """Test status updates with partial data sets."""
        # Only CPU data
        self.entry.set_cpu_seconds_total(3600.0, 1800.0)
        self.assertEqual(self.entry.status, "downloaded")

        # Add energy (still downloaded - need carbon for processed)
        self.entry.set_usage_kwh(2.5, 1.0)
        self.assertEqual(self.entry.status, "downloaded")

        # Add carbon (now processed - has CPU, kwh, and carbon)
        self.entry.set_usage_gco2eq(100.0, 50.0)
        self.assertEqual(self.entry.status, "processed")

        # Add timestamp (still processed - missing user)
        self.entry.set_timestamp(datetime.now())
        self.assertEqual(self.entry.status, "processed")

        # Add user info (now complete - has everything)
        self.entry.set_user_info({"name": "Test"})
        self.assertEqual(self.entry.status, "complete")


if __name__ == '__main__':
    unittest.main()
