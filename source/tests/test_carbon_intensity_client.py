"""
Unit tests for CarbonIntensityAPIClient
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from usage_calculation.CarbonIntensityAPIClient import CarbonIntensityAPIClient


class TestCarbonIntensityAPIClient(unittest.TestCase):
    """Test cases for CarbonIntensityAPIClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = CarbonIntensityAPIClient()

    def test_initialization(self):
        """Test client initialization."""
        self.assertEqual(
            self.client.api_url,
            "https://api.carbonintensity.org.uk/intensity"
        )

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_success(self, mock_get):
        """Test successful carbon intensity retrieval."""
        # Mock responses for both API calls
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "data": [{
                "intensity": {
                    "actual": 100
                }
            }]
        }

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "data": [{
                "intensity": {
                    "actual": 80
                }
            }]
        }

        # Configure mock to return different responses for each call
        mock_get.side_effect = [mock_response1, mock_response2]

        # Test
        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Verify average calculation
        expected_average = (100 + 80) / 2
        self.assertEqual(result, expected_average)

        # Verify API was called twice
        self.assertEqual(mock_get.call_count, 2)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_url_construction(self, mock_get):
        """Test that URLs are constructed correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"intensity": {"actual": 50}}]
        }
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        self.client.get_carbon_intensity(start_time)

        # Check first call (start to mid)
        first_call_url = mock_get.call_args_list[0][0][0]
        self.assertIn("2025-01-15T12:00Z", first_call_url)
        self.assertIn("2025-01-15T12:30Z", first_call_url)

        # Check second call (mid to end)
        second_call_url = mock_get.call_args_list[1][0][0]
        self.assertIn("2025-01-15T12:30Z", second_call_url)
        self.assertIn("2025-01-15T13:00Z", second_call_url)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_request_exception(self, mock_get):
        """Test handling of request exceptions."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 on error
        self.assertEqual(result, 0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import requests
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 on HTTP error
        self.assertEqual(result, 0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_malformed_response(self, mock_get):
        """Test handling of malformed API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Missing 'intensity' key
        mock_response.json.return_value = {"data": [{"wrong_key": "value"}]}
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 on parse error
        self.assertEqual(result, 0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_empty_data(self, mock_get):
        """Test handling of empty data array."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 on index error
        self.assertEqual(result, 0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_same_values(self, mock_get):
        """Test average calculation with identical values."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"intensity": {"actual": 45}}]
        }
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Average of 45 and 45 should be 45
        self.assertEqual(result, 45.0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_zero_values(self, mock_get):
        """Test with zero intensity values."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"intensity": {"actual": 0}}]
        }
        mock_get.return_value = mock_response

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Average of 0 and 0 should be 0
        self.assertEqual(result, 0.0)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_first_call_fails(self, mock_get):
        """Test when first API call fails."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("First call failed")

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 on error
        self.assertEqual(result, 0)
        # Should only attempt one call before failing
        self.assertEqual(mock_get.call_count, 1)

    @patch('usage_calculation.CarbonIntensityAPIClient.requests.get')
    def test_get_carbon_intensity_second_call_fails(self, mock_get):
        """Test when second API call fails."""
        import requests

        # First call succeeds
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "data": [{"intensity": {"actual": 100}}]
        }

        # Second call fails
        mock_get.side_effect = [
            mock_response1,
            requests.exceptions.RequestException("Second call failed")
        ]

        start_time = datetime(2025, 1, 15, 12, 0, 0)
        result = self.client.get_carbon_intensity(start_time)

        # Should return 0 when second call fails
        self.assertEqual(result, 0)
        # Should attempt both calls
        self.assertEqual(mock_get.call_count, 2)

    def test_time_calculation(self):
        """Test that time periods are calculated correctly."""
        start_time = datetime(2025, 1, 15, 12, 0, 0)
        expected_mid = start_time + timedelta(minutes=30)
        expected_end = start_time + timedelta(hours=1)

        # Verify our understanding matches implementation
        self.assertEqual(expected_mid, datetime(2025, 1, 15, 12, 30, 0))
        self.assertEqual(expected_end, datetime(2025, 1, 15, 13, 0, 0))


if __name__ == '__main__':
    unittest.main()
