"""
Unit tests for Machine class
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.Machine import Machine


class TestMachine(unittest.TestCase):
    """Test cases for Machine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.machine = Machine("MUON")

    def test_initialization(self):
        """Test machine initialization."""
        self.assertEqual(self.machine.name, "MUON")

    def test_cpu_seconds_total_structure(self):
        """Test CPU seconds total data structure."""
        # Check busy structure
        self.assertIn("busy", self.machine.cpu_seconds_total)
        self.assertIn("number_data_points", self.machine.cpu_seconds_total["busy"])
        self.assertIn("running_average", self.machine.cpu_seconds_total["busy"])
        self.assertEqual(self.machine.cpu_seconds_total["busy"]["number_data_points"], 0)
        self.assertEqual(self.machine.cpu_seconds_total["busy"]["running_average"], 0)

        # Check idle structure
        self.assertIn("idle", self.machine.cpu_seconds_total)
        self.assertIn("number_data_points", self.machine.cpu_seconds_total["idle"])
        self.assertIn("running_average", self.machine.cpu_seconds_total["idle"])
        self.assertEqual(self.machine.cpu_seconds_total["idle"]["number_data_points"], 0)
        self.assertEqual(self.machine.cpu_seconds_total["idle"]["running_average"], 0)

    def test_energy_kwh_structure(self):
        """Test energy kWh data structure."""
        # Check busy structure
        self.assertIn("busy", self.machine.energy_kwh)
        self.assertIn("number_data_points", self.machine.energy_kwh["busy"])
        self.assertIn("running_average", self.machine.energy_kwh["busy"])
        self.assertEqual(self.machine.energy_kwh["busy"]["number_data_points"], 0)
        self.assertEqual(self.machine.energy_kwh["busy"]["running_average"], 0)

        # Check idle structure
        self.assertIn("idle", self.machine.energy_kwh)
        self.assertIn("number_data_points", self.machine.energy_kwh["idle"])
        self.assertIn("running_average", self.machine.energy_kwh["idle"])
        self.assertEqual(self.machine.energy_kwh["idle"]["number_data_points"], 0)
        self.assertEqual(self.machine.energy_kwh["idle"]["running_average"], 0)

    def test_carbon_gco2eq_structure(self):
        """Test carbon gCO2eq data structure."""
        # Check busy structure
        self.assertIn("busy", self.machine.carbon_gCo2eq)
        self.assertIn("number_data_points", self.machine.carbon_gCo2eq["busy"])
        self.assertIn("running_average", self.machine.carbon_gCo2eq["busy"])
        self.assertEqual(self.machine.carbon_gCo2eq["busy"]["number_data_points"], 0)
        self.assertEqual(self.machine.carbon_gCo2eq["busy"]["running_average"], 0)

        # Check idle structure
        self.assertIn("idle", self.machine.carbon_gCo2eq)
        self.assertIn("number_data_points", self.machine.carbon_gCo2eq["idle"])
        self.assertIn("running_average", self.machine.carbon_gCo2eq["idle"])
        self.assertEqual(self.machine.carbon_gCo2eq["idle"]["number_data_points"], 0)
        self.assertEqual(self.machine.carbon_gCo2eq["idle"]["running_average"], 0)

    def test_machine_name_storage(self):
        """Test that machine name is correctly stored."""
        machine1 = Machine("ATLAS")
        machine2 = Machine("NOVA")
        machine3 = Machine("123-test-machine")

        self.assertEqual(machine1.name, "ATLAS")
        self.assertEqual(machine2.name, "NOVA")
        self.assertEqual(machine3.name, "123-test-machine")

    def test_initial_values_all_zero(self):
        """Test that all initial values are zero."""
        # CPU seconds
        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["running_average"], 0
        )
        self.assertEqual(
            self.machine.cpu_seconds_total["idle"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.cpu_seconds_total["idle"]["running_average"], 0
        )

        # Energy
        self.assertEqual(
            self.machine.energy_kwh["busy"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.energy_kwh["busy"]["running_average"], 0
        )
        self.assertEqual(
            self.machine.energy_kwh["idle"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.energy_kwh["idle"]["running_average"], 0
        )

        # Carbon
        self.assertEqual(
            self.machine.carbon_gCo2eq["busy"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.carbon_gCo2eq["busy"]["running_average"], 0
        )
        self.assertEqual(
            self.machine.carbon_gCo2eq["idle"]["number_data_points"], 0
        )
        self.assertEqual(
            self.machine.carbon_gCo2eq["idle"]["running_average"], 0
        )

    def test_data_structure_independence(self):
        """Test that each machine has independent data structures."""
        machine1 = Machine("Machine1")
        machine2 = Machine("Machine2")

        # Modify machine1 data
        machine1.cpu_seconds_total["busy"]["number_data_points"] = 10
        machine1.cpu_seconds_total["busy"]["running_average"] = 100.5

        # Machine2 should be unaffected
        self.assertEqual(
            machine2.cpu_seconds_total["busy"]["number_data_points"], 0
        )
        self.assertEqual(
            machine2.cpu_seconds_total["busy"]["running_average"], 0
        )

    def test_direct_modification_of_metrics(self):
        """Test that metrics can be directly modified."""
        # Modify CPU seconds
        self.machine.cpu_seconds_total["busy"]["number_data_points"] = 5
        self.machine.cpu_seconds_total["busy"]["running_average"] = 3600.0

        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["number_data_points"], 5
        )
        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["running_average"], 3600.0
        )

        # Modify energy
        self.machine.energy_kwh["idle"]["number_data_points"] = 3
        self.machine.energy_kwh["idle"]["running_average"] = 0.5

        self.assertEqual(
            self.machine.energy_kwh["idle"]["number_data_points"], 3
        )
        self.assertEqual(
            self.machine.energy_kwh["idle"]["running_average"], 0.5
        )

        # Modify carbon
        self.machine.carbon_gCo2eq["busy"]["number_data_points"] = 10
        self.machine.carbon_gCo2eq["busy"]["running_average"] = 45.3

        self.assertEqual(
            self.machine.carbon_gCo2eq["busy"]["number_data_points"], 10
        )
        self.assertEqual(
            self.machine.carbon_gCo2eq["busy"]["running_average"], 45.3
        )

    def test_running_average_calculation_simulation(self):
        """Test simulated running average calculation."""
        # Simulate adding data points
        data_points = 0
        running_avg = 0.0

        # Add first value: 100
        data_points += 1
        running_avg = ((running_avg * (data_points - 1)) + 100) / data_points
        self.machine.cpu_seconds_total["busy"]["number_data_points"] = data_points
        self.machine.cpu_seconds_total["busy"]["running_average"] = running_avg

        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["running_average"], 100.0
        )

        # Add second value: 200
        data_points += 1
        running_avg = ((running_avg * (data_points - 1)) + 200) / data_points
        self.machine.cpu_seconds_total["busy"]["number_data_points"] = data_points
        self.machine.cpu_seconds_total["busy"]["running_average"] = running_avg

        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["running_average"], 150.0
        )

        # Add third value: 300
        data_points += 1
        running_avg = ((running_avg * (data_points - 1)) + 300) / data_points
        self.machine.cpu_seconds_total["busy"]["number_data_points"] = data_points
        self.machine.cpu_seconds_total["busy"]["running_average"] = running_avg

        self.assertEqual(
            self.machine.cpu_seconds_total["busy"]["running_average"], 200.0
        )

    def test_empty_string_machine_name(self):
        """Test machine with empty string name."""
        machine = Machine("")
        self.assertEqual(machine.name, "")

    def test_special_characters_in_name(self):
        """Test machine name with special characters."""
        machine = Machine("Test-Machine_123.example")
        self.assertEqual(machine.name, "Test-Machine_123.example")

    def test_unicode_machine_name(self):
        """Test machine name with unicode characters."""
        machine = Machine("Machine-αβγ-test")
        self.assertEqual(machine.name, "Machine-αβγ-test")


if __name__ == '__main__':
    unittest.main()
