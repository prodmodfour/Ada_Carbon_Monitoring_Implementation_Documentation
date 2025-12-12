"""
Unit tests for PrometheusAPIClient
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prometheus.PrometheusAPIClient import PrometheusAPIClient


class TestPrometheusAPIClient(unittest.TestCase):
    """Test cases for PrometheusAPIClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = PrometheusAPIClient(
            prometheus_url="https://test-prometheus.example.com/",
            api_endpoint="api/v1/query_range",
            timeout=120
        )

    def test_initialization_default(self):
        """Test default initialization."""
        client = PrometheusAPIClient()
        self.assertIn("api/v1/query_range", client.url)
        self.assertEqual(client.timeout, 120)

    def test_initialization_custom(self):
        """Test custom initialization."""
        self.assertEqual(self.client.base_url, "https://test-prometheus.example.com/")
        self.assertEqual(self.client.api_endpoint, "api/v1/query_range")
        self.assertEqual(self.client.timeout, 120)

    def test_url_construction_without_trailing_slash(self):
        """Test URL construction when base URL has no trailing slash."""
        client = PrometheusAPIClient(
            prometheus_url="https://example.com",
            api_endpoint="api/v1/query_range"
        )
        self.assertEqual(client.url, "https://example.com/api/v1/query_range")

    def test_url_construction_with_leading_slash(self):
        """Test URL construction when endpoint has leading slash."""
        client = PrometheusAPIClient(
            prometheus_url="https://example.com/",
            api_endpoint="/api/v1/query_range"
        )
        self.assertEqual(client.url, "https://example.com/api/v1/query_range")

    def test_to_rfc3339_naive_datetime(self):
        """Test RFC3339 formatting with naive datetime."""
        dt = datetime(2025, 1, 15, 12, 30, 45)
        result = self.client._to_rfc3339(dt)
        self.assertEqual(result, "2025-01-15T12:30:45Z")

    def test_to_rfc3339_aware_datetime(self):
        """Test RFC3339 formatting with timezone-aware datetime."""
        dt = datetime(2025, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = self.client._to_rfc3339(dt)
        self.assertEqual(result, "2025-01-15T12:30:45Z")

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_query_success(self, mock_get):
        """Test successful query."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://test-prometheus.example.com/api/v1/query_range?query=test"
        mock_response.reason = "OK"
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"mode": "user"},
                        "values": [[1234567890, "100"]]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Test
        parameters = {
            "query": "test_query",
            "start": "2025-01-15T12:00:00Z",
            "end": "2025-01-15T13:00:00Z",
            "step": "1h"
        }

        result = self.client.query(parameters)

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        mock_get.assert_called_once()

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_query_timeout(self, mock_get):
        """Test query timeout handling."""
        import requests
        mock_get.side_effect = requests.exceptions.ReadTimeout()

        parameters = {"query": "test", "start": "2025-01-15T12:00:00Z"}
        result = self.client.query(parameters)

        self.assertIsNone(result)

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_query_http_error(self, mock_get):
        """Test HTTP error handling."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        parameters = {"query": "test"}
        result = self.client.query(parameters)

        self.assertIsNone(result)

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_query_request_exception(self, mock_get):
        """Test general request exception handling."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        parameters = {"query": "test"}
        result = self.client.query(parameters)

        self.assertIsNone(result)

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_cpu_seconds_total_basic(self, mock_get):
        """Test cpu_seconds_total method with basic parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "metric": {"mode": "user"},
                        "values": [[1234567890, "100"]]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.cpu_seconds_total(
            timestamp=timestamp,
            cloud_project_name="CDAaaS"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

        # Verify the query was constructed correctly
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertIn('cloud_project_name="CDAaaS"', params['query'])
        self.assertIn('increase(node_cpu_seconds_total', params['query'])

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_cpu_seconds_total_with_machine_name(self, mock_get):
        """Test cpu_seconds_total with machine_name filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {"status": "success", "data": {"result": []}}
        mock_get.return_value = mock_response

        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.cpu_seconds_total(
            timestamp=timestamp,
            cloud_project_name="CDAaaS",
            machine_name="MUON"
        )

        # Verify query includes machine_name selector
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertIn('cloud_project_name="CDAaaS"', params['query'])
        self.assertIn('machine_name="MUON"', params['query'])

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_cpu_seconds_total_with_host(self, mock_get):
        """Test cpu_seconds_total with host filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {"status": "success", "data": {"result": []}}
        mock_get.return_value = mock_response

        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.cpu_seconds_total(
            timestamp=timestamp,
            cloud_project_name="CDAaaS",
            machine_name="MUON",
            host="172.16.100.50"
        )

        # Verify query includes host selector
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertIn('host="172.16.100.50"', params['query'])
        self.assertIn('machine_name="MUON"', params['query'])
        self.assertIn('cloud_project_name="CDAaaS"', params['query'])

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_cpu_seconds_total_custom_step(self, mock_get):
        """Test cpu_seconds_total with custom step parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {"status": "success", "data": {"result": []}}
        mock_get.return_value = mock_response

        timestamp = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.cpu_seconds_total(
            timestamp=timestamp,
            cloud_project_name="CDAaaS",
            step="30m"
        )

        # Verify custom step was used in query
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertEqual(params['step'], "30m")
        self.assertIn('[30m]', params['query'])

    def test_cpu_seconds_total_query_construction(self):
        """Test that query is properly constructed for cpu_seconds_total."""
        timestamp = datetime(2025, 1, 15, 12, 0, 0)

        # Mock the query method to inspect what parameters it receives
        with patch.object(self.client, 'query') as mock_query:
            mock_query.return_value = {"status": "success"}

            self.client.cpu_seconds_total(
                timestamp=timestamp,
                cloud_project_name="CDAaaS",
                machine_name="MUON",
                host="172.16.100.50"
            )

            # Verify query was called
            mock_query.assert_called_once()

            # Get the parameters passed to query
            call_args = mock_query.call_args[0][0]

            # Check query structure
            self.assertIn("query", call_args)
            self.assertIn("increase(node_cpu_seconds_total", call_args["query"])
            self.assertIn('cloud_project_name="CDAaaS"', call_args["query"])
            self.assertIn('machine_name="MUON"', call_args["query"])
            self.assertIn('host="172.16.100.50"', call_args["query"])
            self.assertIn("start", call_args)
            self.assertIn("end", call_args)
            self.assertIn("step", call_args)

            # Verify timestamps are RFC3339 formatted
            self.assertEqual(call_args["start"], "2025-01-15T12:00:00Z")
            self.assertEqual(call_args["end"], "2025-01-15T12:00:00Z")


if __name__ == '__main__':
    unittest.main()
