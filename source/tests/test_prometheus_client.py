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

    def test_url_property(self):
        """Test that URL property is correctly formed."""
        self.assertEqual(
            self.client.url,
            "https://test-prometheus.example.com/api/v1/query_range"
        )

    def test_base_url_property(self):
        """Test that base URL is stored correctly."""
        self.assertEqual(
            self.client.base_url,
            "https://test-prometheus.example.com/"
        )

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
    def test_query_with_custom_parameters(self, mock_get):
        """Test query method with custom parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {
            "status": "success",
            "data": {"result": []}
        }
        mock_get.return_value = mock_response

        parameters = {
            "query": "up",
            "start": "2025-01-15T12:00:00Z",
            "end": "2025-01-15T13:00:00Z"
        }

        result = self.client.query(parameters)

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

        # Verify parameters were passed correctly
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params'], parameters)

    @patch('prometheus.PrometheusAPIClient.requests.get')
    def test_query_with_step_parameter(self, mock_get):
        """Test query with step parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "test_url"
        mock_response.reason = "OK"
        mock_response.json.return_value = {"status": "success", "data": {"result": []}}
        mock_get.return_value = mock_response

        parameters = {
            "query": "rate(metric[5m])",
            "start": "2025-01-15T12:00:00Z",
            "end": "2025-01-15T13:00:00Z",
            "step": "1m"
        }

        result = self.client.query(parameters)

        # Verify step was passed
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]['params']['step'], "1m")


if __name__ == '__main__':
    unittest.main()
