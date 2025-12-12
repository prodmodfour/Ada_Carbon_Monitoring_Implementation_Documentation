"""
Unit tests for WorkspaceTracker
Integration tests with mocked external dependencies
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workspace_tracking.WorkspaceTracker import WorkspaceTracker
from workspace_tracking.WorkspaceUsageEntry import WorkspaceUsageEntry


class TestWorkspaceTracker(unittest.TestCase):
    """Test cases for WorkspaceTracker class."""

    def setUp(self):
        """Set up test fixtures with mocked clients."""
        # Patch all external clients
        self.mongo_patcher = patch('workspace_tracking.WorkspaceTracker.MongoDBClient')
        self.prom_patcher = patch('workspace_tracking.WorkspaceTracker.PrometheusAPIClient')
        self.carbon_patcher = patch('workspace_tracking.WorkspaceTracker.CarbonIntensityAPIClient')

        self.mock_mongo = self.mongo_patcher.start()
        self.mock_prom = self.prom_patcher.start()
        self.mock_carbon = self.mock_carbon_patcher.start()

        # Create tracker instance
        self.tracker = WorkspaceTracker(
            mongo_uri="mongodb://test:27017/",
            mongo_db="test_ada",
            prometheus_url="https://test-prometheus/"
        )

    def tearDown(self):
        """Clean up patches."""
        self.mongo_patcher.stop()
        self.prom_patcher.stop()
        self.carbon_patcher.stop()

    def test_initialization(self):
        """Test tracker initialization."""
        self.assertIsNotNone(self.tracker.mongo_client)
        self.assertIsNotNone(self.tracker.prometheus_client)
        self.assertIsNotNone(self.tracker.carbon_client)
        self.assertIsNotNone(self.tracker.equivalency_calc)
        self.assertIsNotNone(self.tracker.carbon_calculator)
        self.assertIsNotNone(self.tracker.electricity_estimator)
        self.assertEqual(self.tracker.default_cpu_tdp_w, 100.0)
        self.assertIsInstance(self.tracker.tracked_workspaces, dict)

    def test_initialization_with_credentials(self):
        """Test initialization with MongoDB credentials."""
        with patch('workspace_tracking.WorkspaceTracker.MongoDBClient') as mock_client:
            tracker = WorkspaceTracker(
                mongo_uri="mongodb://test:27017/",
                mongo_db="test_ada",
                mongo_user="testuser",
                mongo_pass="testpass"
            )

            # Verify MongoDBClient was called with credentials
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args[1]
            self.assertEqual(call_kwargs['username'], "testuser")
            self.assertEqual(call_kwargs['password'], "testpass")

    def test_electricity_estimator_constants(self):
        """Test that electricity estimator has correct power constants."""
        # Should use 12W busy, 1W idle as per specification
        self.assertEqual(self.tracker.electricity_estimator.busy_power_w, 12.0)
        self.assertEqual(self.tracker.electricity_estimator.idle_power_w, 1.0)

    def test_tracked_workspaces_storage(self):
        """Test that tracked workspaces can be stored and retrieved."""
        entry = WorkspaceUsageEntry(
            workspace_id="test_workspace_1",
            hostname="172.16.100.50",
            owner="test.user"
        )

        self.tracker.tracked_workspaces["test_workspace_1"] = entry

        self.assertIn("test_workspace_1", self.tracker.tracked_workspaces)
        retrieved = self.tracker.tracked_workspaces["test_workspace_1"]
        self.assertEqual(retrieved.workspace_id, "test_workspace_1")
        self.assertEqual(retrieved.hostname, "172.16.100.50")

    def test_multiple_workspace_tracking(self):
        """Test tracking multiple workspaces simultaneously."""
        entry1 = WorkspaceUsageEntry("ws1", "host1", "user1")
        entry2 = WorkspaceUsageEntry("ws2", "host2", "user2")
        entry3 = WorkspaceUsageEntry("ws3", "host3", "user3")

        self.tracker.tracked_workspaces["ws1"] = entry1
        self.tracker.tracked_workspaces["ws2"] = entry2
        self.tracker.tracked_workspaces["ws3"] = entry3

        self.assertEqual(len(self.tracker.tracked_workspaces), 3)
        self.assertIn("ws1", self.tracker.tracked_workspaces)
        self.assertIn("ws2", self.tracker.tracked_workspaces)
        self.assertIn("ws3", self.tracker.tracked_workspaces)

    def test_default_tdp_configuration(self):
        """Test custom default TDP configuration."""
        tracker = WorkspaceTracker(default_cpu_tdp_w=150.0)
        self.assertEqual(tracker.default_cpu_tdp_w, 150.0)

    def test_prometheus_url_configuration(self):
        """Test custom Prometheus URL configuration."""
        with patch('workspace_tracking.WorkspaceTracker.PrometheusAPIClient') as mock_prom:
            tracker = WorkspaceTracker(
                prometheus_url="https://custom-prometheus.example.com/"
            )

            # Verify PrometheusAPIClient was called with custom URL
            mock_prom.assert_called_once()
            call_kwargs = mock_prom.call_args[1]
            self.assertEqual(
                call_kwargs['prometheus_url'],
                "https://custom-prometheus.example.com/"
            )

    def test_workspace_entry_integration(self):
        """Test that WorkspaceUsageEntry integrates correctly."""
        entry = WorkspaceUsageEntry("test_ws", "test_host", "test_owner")

        # Simulate tracking workflow
        entry.set_timestamp(datetime(2025, 1, 15, 12, 0, 0))
        entry.set_user_info({"platform_name": "test_owner"})
        entry.set_cpu_seconds_total(3600.0, 1800.0)
        entry.set_usage_kwh(0.012, 0.0005)  # 12W busy, 1W idle
        entry.set_usage_gco2eq(0.54, 0.0225, carbon_intensity=45.0)

        # Store in tracker
        self.tracker.tracked_workspaces["test_ws"] = entry

        # Verify complete workflow
        retrieved = self.tracker.tracked_workspaces["test_ws"]
        self.assertEqual(retrieved.status, "complete")
        self.assertIsNotNone(retrieved.timestamp)
        self.assertIsNotNone(retrieved.user_info)

    def test_client_references(self):
        """Test that client references are properly stored."""
        self.assertIsNotNone(self.tracker.mongo_client)
        self.assertIsNotNone(self.tracker.prometheus_client)
        self.assertIsNotNone(self.tracker.carbon_client)

        # Verify they are different objects
        self.assertIsNot(self.tracker.mongo_client, self.tracker.prometheus_client)
        self.assertIsNot(self.tracker.prometheus_client, self.tracker.carbon_client)

    def test_calculation_helpers_initialization(self):
        """Test that calculation helpers are properly initialized."""
        # CarbonCalculator should be initialized with carbon_client
        self.assertIsNotNone(self.tracker.carbon_calculator)

        # ElectricityEstimator should have correct constants
        self.assertEqual(self.tracker.electricity_estimator.busy_power_w, 12.0)
        self.assertEqual(self.tracker.electricity_estimator.idle_power_w, 1.0)

    def test_empty_tracked_workspaces_initial_state(self):
        """Test that tracked_workspaces starts empty."""
        tracker = WorkspaceTracker()
        self.assertEqual(len(tracker.tracked_workspaces), 0)
        self.assertIsInstance(tracker.tracked_workspaces, dict)

    def test_equivalency_calculator_integration(self):
        """Test that CarbonEquivalencyCalculator is available."""
        self.assertIsNotNone(self.tracker.equivalency_calc)

        # Test that it can calculate equivalencies
        result = self.tracker.equivalency_calc.calculate_equivalencies(100.0)
        self.assertIn("equivalencies", result)
        self.assertIn("miles_driven_car", result["equivalencies"])

    def test_workspace_cleanup(self):
        """Test removing workspaces from tracking."""
        entry = WorkspaceUsageEntry("test_ws", "test_host", "test_owner")
        self.tracker.tracked_workspaces["test_ws"] = entry

        self.assertIn("test_ws", self.tracker.tracked_workspaces)

        # Remove workspace
        del self.tracker.tracked_workspaces["test_ws"]

        self.assertNotIn("test_ws", self.tracker.tracked_workspaces)

    def test_workspace_overwrite(self):
        """Test overwriting an existing workspace entry."""
        entry1 = WorkspaceUsageEntry("test_ws", "host1", "user1")
        entry2 = WorkspaceUsageEntry("test_ws", "host2", "user2")

        self.tracker.tracked_workspaces["test_ws"] = entry1
        self.assertEqual(
            self.tracker.tracked_workspaces["test_ws"].hostname, "host1"
        )

        self.tracker.tracked_workspaces["test_ws"] = entry2
        self.assertEqual(
            self.tracker.tracked_workspaces["test_ws"].hostname, "host2"
        )

    def test_concurrent_workspace_tracking(self):
        """Test tracking workspaces with different statuses."""
        ws1 = WorkspaceUsageEntry("ws1", "host1", "user1")
        ws1.set_cpu_seconds_total(3600.0, 1800.0)

        ws2 = WorkspaceUsageEntry("ws2", "host2", "user2")
        ws2.set_timestamp(datetime.now())
        ws2.set_user_info({"name": "User 2"})
        ws2.set_cpu_seconds_total(7200.0, 3600.0)
        ws2.set_usage_kwh(0.024, 0.001)
        ws2.set_usage_gco2eq(1.08, 0.045)

        ws3 = WorkspaceUsageEntry("ws3", "host3", "user3")

        self.tracker.tracked_workspaces["ws1"] = ws1
        self.tracker.tracked_workspaces["ws2"] = ws2
        self.tracker.tracked_workspaces["ws3"] = ws3

        # Verify different statuses
        self.assertEqual(
            self.tracker.tracked_workspaces["ws1"].status, "downloaded"
        )
        self.assertEqual(
            self.tracker.tracked_workspaces["ws2"].status, "complete"
        )
        self.assertEqual(
            self.tracker.tracked_workspaces["ws3"].status, "initialized"
        )


if __name__ == '__main__':
    unittest.main()
