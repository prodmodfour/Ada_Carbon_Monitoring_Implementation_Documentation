"""
Unit tests for MongoDBClient
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb.MongoDBClient import MongoDBClient


class TestMongoDBClient(unittest.TestCase):
    """Test cases for MongoDBClient class."""

    def setUp(self):
        """Set up test fixtures with mocked MongoDB."""
        # Patch MongoClient to avoid actual database connection
        self.patcher = patch('mongodb.MongoDBClient.MongoClient')
        self.mock_mongo_client = self.patcher.start()

        # Create mock database and collections
        self.mock_db = MagicMock()
        self.mock_mongo_client.return_value.__getitem__.return_value = self.mock_db

        # Initialize client
        self.client = MongoDBClient(
            mongo_uri="mongodb://localhost:27017/",
            database_name="test_ada"
        )

    def tearDown(self):
        """Clean up."""
        self.patcher.stop()

    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client.client)
        self.assertIsNotNone(self.client.db)
        self.assertEqual(self.client.database_name, "test_ada")

    def test_initialization_with_auth(self):
        """Test initialization with username and password."""
        with patch('mongodb.MongoDBClient.MongoClient') as mock_client:
            client = MongoDBClient(
                mongo_uri="mongodb://localhost:27017/",
                database_name="test_ada",
                username="testuser",
                password="testpass"
            )

            # Check that URI was modified to include credentials
            self.assertIn("testuser", client.mongo_uri)
            self.assertIn("testpass", client.mongo_uri)

    def test_get_user_by_host_and_time_success(self):
        """Test successful user retrieval by host and time."""
        # Mock workspace data
        mock_workspace = {
            "_id": "workspace123",
            "hostname": "172.16.100.50",
            "owner": "john.doe",
            "created_time": datetime(2025, 1, 1, 10, 0, 0),
            "acquired_time": datetime(2025, 1, 1, 11, 0, 0),
            "deleted_time": None
        }

        # Mock user data
        mock_user = {
            "_id": "user123",
            "platform_name": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "uid": 1001
        }

        # Setup mock collections
        mock_workspaces = MagicMock()
        mock_users = MagicMock()

        mock_workspaces.find.return_value = [mock_workspace]
        mock_users.find_one.return_value = mock_user

        self.mock_db.__getitem__.side_effect = lambda x: {
            "workspaces": mock_workspaces,
            "users": mock_users
        }[x]

        # Test
        result = self.client.get_user_by_host_and_time(
            hostname="172.16.100.50",
            timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["platform_name"], "john.doe")
        self.assertEqual(result["name"], "John Doe")

    def test_get_user_by_host_and_time_no_workspace(self):
        """Test when no workspace is found."""
        mock_workspaces = MagicMock()
        mock_workspaces.find.return_value = []

        self.mock_db.__getitem__.return_value = mock_workspaces

        result = self.client.get_user_by_host_and_time(
            hostname="nonexistent.host",
            timestamp=datetime(2025, 1, 1, 12, 0, 0)
        )

        self.assertIsNone(result)

    def test_get_user_by_host_and_time_workspace_deleted(self):
        """Test when workspace was deleted before timestamp."""
        mock_workspace = {
            "_id": "workspace123",
            "hostname": "172.16.100.50",
            "owner": "john.doe",
            "created_time": datetime(2025, 1, 1, 10, 0, 0),
            "acquired_time": datetime(2025, 1, 1, 11, 0, 0),
            "deleted_time": datetime(2025, 1, 1, 11, 30, 0)  # Deleted before query time
        }

        mock_workspaces = MagicMock()
        mock_workspaces.find.return_value = [mock_workspace]

        self.mock_db.__getitem__.return_value = mock_workspaces

        result = self.client.get_user_by_host_and_time(
            hostname="172.16.100.50",
            timestamp=datetime(2025, 1, 1, 12, 0, 0)  # After deletion
        )

        self.assertIsNone(result)

    def test_get_group_by_cloud_project_and_machine(self):
        """Test group retrieval by cloud project and machine."""
        mock_group = {
            "_id": "group123",
            "name": "CDAaaS_MUON",
            "gid": 2001,
            "members": ["user1", "user2"]
        }

        mock_groups = MagicMock()
        mock_groups.find_one.return_value = mock_group

        self.mock_db.__getitem__.return_value = mock_groups

        result = self.client.get_group_by_cloud_project_and_machine(
            cloud_project_name="CDAaaS",
            machine_name="MUON"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "CDAaaS_MUON")
        self.assertEqual(result["gid"], 2001)

    def test_get_group_not_found(self):
        """Test when group is not found."""
        mock_groups = MagicMock()
        mock_groups.find_one.return_value = None

        self.mock_db.__getitem__.return_value = mock_groups

        result = self.client.get_group_by_cloud_project_and_machine(
            cloud_project_name="NonExistent",
            machine_name="Project"
        )

        self.assertIsNone(result)

    def test_get_all_groups_for_cloud_project(self):
        """Test retrieving all groups for a cloud project."""
        mock_groups_list = [
            {"name": "CDAaaS_MUON", "gid": 2001},
            {"name": "CDAaaS_NOVA", "gid": 2002},
            {"name": "CDAaaS_ATLAS", "gid": 2003}
        ]

        mock_groups = MagicMock()
        mock_groups.find.return_value = mock_groups_list

        self.mock_db.__getitem__.return_value = mock_groups

        result = self.client.get_all_groups_for_cloud_project("CDAaaS")

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["name"], "CDAaaS_MUON")

    def test_attribute_usage_to_user(self):
        """Test attributing usage to user."""
        mock_user = {
            "platform_name": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "uid": 1001
        }

        # Mock the get_user_by_host_and_time method
        self.client.get_user_by_host_and_time = Mock(return_value=mock_user)

        result = self.client.attribute_usage_to_user(
            hostname="172.16.100.50",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            cpu_usage=3600.0,
            additional_metrics={"carbon_intensity": 45.0}
        )

        self.assertIsNotNone(result)
        self.assertIn("user", result)
        self.assertIn("usage", result)
        self.assertEqual(result["user"]["platform_name"], "john.doe")
        self.assertEqual(result["usage"]["cpu_usage_seconds"], 3600.0)
        self.assertEqual(result["usage"]["carbon_intensity"], 45.0)

    def test_attribute_usage_to_user_no_user(self):
        """Test attribution when user is not found."""
        self.client.get_user_by_host_and_time = Mock(return_value=None)

        result = self.client.attribute_usage_to_user(
            hostname="nonexistent.host",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            cpu_usage=3600.0
        )

        self.assertIsNone(result)

    def test_attribute_usage_to_group(self):
        """Test attributing usage to group."""
        mock_group = {
            "name": "CDAaaS_MUON",
            "gid": 2001,
            "type": "project",
            "members": ["user1", "user2"]
        }

        self.client.get_group_by_cloud_project_and_machine = Mock(return_value=mock_group)

        result = self.client.attribute_usage_to_group(
            cloud_project_name="CDAaaS",
            machine_name="MUON",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            cpu_usage=7200.0,
            additional_metrics={"memory_usage_mb": 8192}
        )

        self.assertIsNotNone(result)
        self.assertIn("group", result)
        self.assertIn("usage", result)
        self.assertEqual(result["group"]["name"], "CDAaaS_MUON")
        self.assertEqual(result["usage"]["cpu_usage_seconds"], 7200.0)

    def test_get_user_by_platform_name(self):
        """Test retrieving user by platform name."""
        mock_user = {
            "platform_name": "john.doe",
            "name": "John Doe",
            "email": "john.doe@example.com"
        }

        mock_users = MagicMock()
        mock_users.find_one.return_value = mock_user

        self.mock_db.__getitem__.return_value = mock_users

        result = self.client.get_user_by_platform_name("john.doe")

        self.assertIsNotNone(result)
        self.assertEqual(result["platform_name"], "john.doe")

    def test_get_workspaces_by_hostname(self):
        """Test retrieving workspaces by hostname."""
        mock_workspaces_list = [
            {
                "hostname": "172.16.100.50",
                "created_time": datetime(2025, 1, 1, 10, 0, 0)
            },
            {
                "hostname": "172.16.100.50",
                "created_time": datetime(2025, 1, 2, 10, 0, 0)
            }
        ]

        mock_workspaces = MagicMock()
        mock_workspaces.find.return_value = mock_workspaces_list

        self.mock_db.__getitem__.return_value = mock_workspaces

        result = self.client.get_workspaces_by_hostname("172.16.100.50")

        self.assertEqual(len(result), 2)

    def test_get_workspaces_by_hostname_with_time_range(self):
        """Test retrieving workspaces with time range filter."""
        mock_workspaces = MagicMock()
        mock_workspaces.find.return_value = []

        self.mock_db.__getitem__.return_value = mock_workspaces

        result = self.client.get_workspaces_by_hostname(
            hostname="172.16.100.50",
            start_time=datetime(2025, 1, 1, 0, 0, 0),
            end_time=datetime(2025, 1, 31, 23, 59, 59)
        )

        # Verify the query was called
        mock_workspaces.find.assert_called_once()
        self.assertIsInstance(result, list)

    def test_close(self):
        """Test closing the connection."""
        # Should not raise an exception
        self.client.close()

        # Verify close was called on the mock
        self.mock_mongo_client.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
