"""
Unit tests for CarbonEquivalencyCalculator
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workspace_tracking.CarbonEquivalencyCalculator import CarbonEquivalencyCalculator


class TestCarbonEquivalencyCalculator(unittest.TestCase):
    """Test cases for CarbonEquivalencyCalculator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.calculator = CarbonEquivalencyCalculator()

    def test_initialization(self):
        """Test calculator initialization."""
        self.assertIsNotNone(self.calculator)
        self.assertIsInstance(self.calculator.EQUIVALENCIES, dict)

    def test_equivalency_factors_exist(self):
        """Test that all expected equivalency factors are defined."""
        expected_factors = [
            "miles_driven_car",
            "smartphone_charge",
            "streaming_hour",
            "kettle_boil",
            "led_bulb_hour",
            "kg_coal_burned"
        ]

        for factor in expected_factors:
            self.assertIn(factor, self.calculator.EQUIVALENCIES)

    def test_calculate_equivalencies_basic(self):
        """Test basic equivalency calculation."""
        gco2eq = 1000  # 1 kg

        result = self.calculator.calculate_equivalencies(gco2eq)

        self.assertIn("total_gco2eq", result)
        self.assertIn("equivalencies", result)
        self.assertEqual(result["total_gco2eq"], 1000)

        # Check that equivalencies were calculated
        self.assertGreater(len(result["equivalencies"]), 0)

    def test_calculate_equivalencies_zero(self):
        """Test with zero emissions."""
        result = self.calculator.calculate_equivalencies(0)

        self.assertEqual(result["total_gco2eq"], 0)
        self.assertEqual(len(result["equivalencies"]), 0)

    def test_calculate_equivalencies_negative(self):
        """Test with negative emissions (should return zero)."""
        result = self.calculator.calculate_equivalencies(-100)

        self.assertEqual(result["total_gco2eq"], 0)
        self.assertEqual(len(result["equivalencies"]), 0)

    def test_miles_driven_calculation(self):
        """Test miles driven equivalency."""
        gco2eq = 400  # Exactly one mile worth

        result = self.calculator.calculate_equivalencies(gco2eq)

        miles = result["equivalencies"]["miles_driven"]["value"]
        self.assertAlmostEqual(miles, 1.0, places=2)

    def test_smartphone_charges_calculation(self):
        """Test smartphone charges equivalency."""
        gco2eq = 8.22  # Exactly one smartphone charge

        result = self.calculator.calculate_equivalencies(gco2eq)

        charges = result["equivalencies"]["smartphone_charges"]["value"]
        self.assertAlmostEqual(charges, 1.0, places=2)

    def test_streaming_hours_calculation(self):
        """Test streaming hours equivalency."""
        gco2eq = 55  # Exactly one hour of streaming

        result = self.calculator.calculate_equivalencies(gco2eq)

        hours = result["equivalencies"]["streaming_hours"]["value"]
        self.assertAlmostEqual(hours, 1.0, places=2)

    def test_kettles_boiled_calculation(self):
        """Test kettles boiled equivalency."""
        gco2eq = 70  # Exactly one liter boiled

        result = self.calculator.calculate_equivalencies(gco2eq)

        liters = result["equivalencies"]["kettles_boiled"]["value"]
        self.assertAlmostEqual(liters, 1.0, places=2)

    def test_get_top_equivalencies(self):
        """Test getting top N equivalencies."""
        gco2eq = 1000

        result = self.calculator.get_top_equivalencies(gco2eq, count=5)

        self.assertIn("total_gco2eq", result)
        self.assertIn("top_equivalencies", result)
        self.assertEqual(result["total_gco2eq"], 1000)

        # Should return exactly 5 equivalencies
        self.assertEqual(len(result["top_equivalencies"]), 5)

    def test_get_top_equivalencies_more_than_available(self):
        """Test requesting more equivalencies than available."""
        gco2eq = 100

        result = self.calculator.get_top_equivalencies(gco2eq, count=100)

        # Should return all available equivalencies
        all_equivs = self.calculator.calculate_equivalencies(gco2eq)
        self.assertEqual(
            len(result["top_equivalencies"]),
            len(all_equivs["equivalencies"])
        )

    def test_format_equivalency_small_value(self):
        """Test formatting small equivalency values."""
        equiv = {
            "value": 0.005,
            "unit": "charges",
            "description": "Smartphone charges"
        }

        result = self.calculator.format_equivalency(equiv)

        self.assertIn("0.0050", result)
        self.assertIn("charges", result)
        self.assertIn("Smartphone charges", result)

    def test_format_equivalency_medium_value(self):
        """Test formatting medium equivalency values."""
        equiv = {
            "value": 5.5,
            "unit": "miles",
            "description": "Miles driven"
        }

        result = self.calculator.format_equivalency(equiv)

        self.assertIn("5.5", result)
        self.assertIn("miles", result)

    def test_format_equivalency_large_value(self):
        """Test formatting large equivalency values."""
        equiv = {
            "value": 1234,
            "unit": "charges",
            "description": "Smartphone charges"
        }

        result = self.calculator.format_equivalency(equiv)

        self.assertIn("1234", result)
        self.assertIn("charges", result)

    def test_format_all_equivalencies(self):
        """Test formatting all equivalencies as string."""
        gco2eq = 500

        result = self.calculator.format_all_equivalencies(gco2eq)

        self.assertIsInstance(result, str)
        self.assertIn("500.00 gCO2eq", result)
        self.assertIn("Equivalencies:", result)

    def test_equivalency_descriptions(self):
        """Test that all equivalencies have descriptions."""
        gco2eq = 100

        result = self.calculator.calculate_equivalencies(gco2eq)

        for key, equiv in result["equivalencies"].items():
            self.assertIn("value", equiv)
            self.assertIn("unit", equiv)
            self.assertIn("description", equiv)
            self.assertIsInstance(equiv["description"], str)
            self.assertGreater(len(equiv["description"]), 0)


if __name__ == '__main__':
    unittest.main()
