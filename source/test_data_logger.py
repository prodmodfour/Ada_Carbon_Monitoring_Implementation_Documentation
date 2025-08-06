import unittest
from unittest.mock import patch, Mock, MagicMock

import data_logger

class TestDataLogger(unittest.TestCase):
    """
    A comprehensive test suite for the data_logger script.
    It uses mocking to isolate functions from external services like Prometheus,
    web APIs, and the database, ensuring that only the application's logic is tested.
    """

    @patch('data_logger.PrometheusConnect')
    def test_connect_to_prometheus_success(self, mock_prometheus_connect):
        """
        Verify that a valid PrometheusConnect object is returned on a successful connection.
        """
        mock_instance = mock_prometheus_connect.return_value
        mock_instance.check_prometheus_connection.return_value = True

        prom_client = data_logger.connect_to_prometheus("http://fake-prometheus.com")

        self.assertIsNotNone(prom_client)
        mock_prometheus_connect.assert_called_once_with(url="http://fake-prometheus.com", disable_ssl=True)
        mock_instance.check_prometheus_connection.assert_called_once()

    @patch('data_logger.PrometheusConnect')
    def test_connect_to_prometheus_connection_check_fails(self, mock_prometheus_connect):
        """
        Verify that None is returned if the connection check fails.
        """
        mock_instance = mock_prometheus_connect.return_value
        mock_instance.check_prometheus_connection.return_value = False

        prom_client = data_logger.connect_to_prometheus("http://fake-prometheus.com")

        self.assertIsNone(prom_client)

    @patch('data_logger.PrometheusConnect', side_effect=Exception("Connection timed out"))
    def test_connect_to_prometheus_raises_exception(self, mock_prometheus_connect):
        """
        Verify that None is returned if PrometheusConnect raises an exception during instantiation.
        """
        prom_client = data_logger.connect_to_prometheus("http://fake-prometheus.com")

        self.assertIsNone(prom_client)
        mock_prometheus_connect.assert_called_once()


    def test_fetch_latest_metrics_success(self):
        """
        Verify that metrics are correctly fetched and parsed when the Prometheus API returns valid data.
        """
        mock_prom_connection = Mock()
        mock_prom_connection.get_current_metric_value.side_effect = [
            [{'value': [0, '1234.5']}],  # cpu_seconds_total
            [{'value': [0, '5368709120']}] # memory_active_bytes (5 GB)
        ]

        metrics = data_logger.fetch_latest_metrics(mock_prom_connection)

        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics['cpu_seconds_total'], 1234.5)
        self.assertEqual(metrics['memory_active_bytes'], 5368709120.0)

    def test_fetch_latest_metrics_partial_failure(self):
        """
        Verify that the function handles cases where some metrics are missing or cause errors,
        and defaults their values to 0.
        """
        mock_prom_connection = Mock()
        mock_prom_connection.get_current_metric_value.side_effect = [
            [{'value': [0, '1234.5']}],  # cpu_seconds_total
            []  # memory_active_bytes returns no data
        ]

        metrics = data_logger.fetch_latest_metrics(mock_prom_connection)

        self.assertEqual(metrics['cpu_seconds_total'], 1234.5)
        self.assertEqual(metrics['memory_active_bytes'], 0)

    def test_fetch_latest_metrics_total_failure(self):
        """
        Verify that the function returns all zeros if the Prometheus API raises exceptions for all metrics.
        """
        mock_prom_connection = Mock()
        mock_prom_connection.get_current_metric_value.side_effect = Exception("Metric not found")

        metrics = data_logger.fetch_latest_metrics(mock_prom_connection)

        self.assertEqual(metrics['cpu_seconds_total'], 0)
        self.assertEqual(metrics['memory_active_bytes'], 0)


    @patch('data_logger.requests.get')
    def test_get_carbon_intensity_success_with_actual(self, mock_get):
        """
        Verify that the 'actual' carbon intensity value is returned when available.
        """
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'intensity': {'forecast': 150, 'actual': 155, 'index': 'moderate'}}]
        }
        mock_response.raise_for_status = Mock() 
        mock_get.return_value = mock_response

        intensity = data_logger.get_carbon_intensity()

        self.assertEqual(intensity, 155)
        mock_get.assert_called_once_with(data_logger.CARBON_INTENSITY_API_URL)

    @patch('data_logger.requests.get')
    def test_get_carbon_intensity_fallback_to_forecast(self, mock_get):
        """
        Verify that the 'forecast' value is used when 'actual' is null.
        """
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'intensity': {'forecast': 150, 'actual': None, 'index': 'moderate'}}]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        intensity = data_logger.get_carbon_intensity()


        self.assertEqual(intensity, 150)

    @patch('data_logger.requests.get')
    def test_get_carbon_intensity_api_error(self, mock_get):
        """
        Verify that 0 is returned if the API call fails.
        """

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API is down")
        mock_get.return_value = mock_response

        intensity = data_logger.get_carbon_intensity()


        self.assertEqual(intensity, 0)




    def test_estimate_power_watts_calculation(self):
        """
        Verify the power estimation calculation with typical metric values.
        """

        previous_metrics = {'cpu_seconds_total': 1000.0, 'memory_active_bytes': 2 * 1024**3} 
        current_metrics = {'cpu_seconds_total': 1060.0, 'memory_active_bytes': 4 * 1024**3} 


        expected_watts = 71.6

        estimated_watts = data_logger.estimate_power_watts(current_metrics, previous_metrics)

        self.assertAlmostEqual(estimated_watts, expected_watts, places=4)

    def test_estimate_power_watts_initial_run(self):
        """
        Verify the calculation when there are no previous metrics (first run).
        CPU usage over the interval should be treated as zero.
        """
        previous_metrics = {}
        current_metrics = {'cpu_seconds_total': 1060.0, 'memory_active_bytes': 4 * 1024**3} # 4 GB


        expected_watts = 51.6

        estimated_watts = data_logger.estimate_power_watts(current_metrics, previous_metrics)

        self.assertAlmostEqual(estimated_watts, expected_watts, places=4)

    def test_estimate_power_watts_missing_keys(self):
        """
        Verify the function handles missing keys in the metric dictionaries gracefully.
        """
        previous_metrics = {'cpu_seconds_total': 1000.0}
        current_metrics = {'memory_active_bytes': 4 * 1024**3}


        expected_watts = 51.6

        estimated_watts = data_logger.estimate_power_watts(current_metrics, previous_metrics)
        self.assertAlmostEqual(estimated_watts, expected_watts, places=4)


    @patch('data_logger.add_reading')
    @patch('data_logger.get_carbon_intensity')
    @patch('data_logger.fetch_latest_metrics')
    @patch('data_logger.connect_to_prometheus')
    @patch('data_logger.time.sleep') 
    def test_logging_loop_single_successful_iteration(
        self, mock_sleep, mock_connect, mock_fetch, mock_intensity, mock_add_reading
    ):
        """
        Verify the logic of a single iteration of the main loop.
        This test ensures all functions are called correctly and the final data
        is passed to the database.
        """

        mock_prom_client = Mock()
        mock_connect.return_value = mock_prom_client


        initial_metrics = {'cpu_seconds_total': 1000.0, 'memory_active_bytes': 2 * 1024**3}
        current_metrics = {'cpu_seconds_total': 1060.0, 'memory_active_bytes': 4 * 1024**3}
        mock_fetch.side_effect = [initial_metrics, current_metrics]

        mock_intensity.return_value = 200 

        with patch('builtins.True', side_effect=[True, False]):
            data_logger.start_logging()

        mock_connect.assert_called_once_with(data_logger.PROMETHEUS_URL)
        self.assertEqual(mock_fetch.call_count, 2)
        mock_intensity.assert_called_once()
        mock_add_reading.assert_called_once()

        expected_watts = 71.6
        interval_hours = data_logger.MONITORING_INTERVAL_SECONDS / 3600
        expected_kwh = expected_watts * interval_hours
        expected_gco2eq = expected_kwh * 200

        args, _ = mock_add_reading.call_args
        
        self.assertAlmostEqual(args[0], expected_watts, places=4)   
        self.assertEqual(args[1], 200)                              
        self.assertAlmostEqual(args[2], expected_gco2eq, places=4)  


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
