"""
Carbon Equivalency Calculator
Converts carbon emissions (gCO2eq) into relatable real-world equivalencies
"""
from typing import Dict, Any


class CarbonEquivalencyCalculator:
    """
    Calculate carbon equivalencies to make emissions more understandable.

    Common equivalencies:
    - Miles driven in average passenger vehicle
    - Trees needed to sequester carbon
    - Smartphone charges
    - Hours of LED light bulb usage
    - Kg of coal burned
    """

    # Conversion factors (gCO2eq per unit)
    # Sources: EPA Greenhouse Gas Equivalencies Calculator (2024 factors),
    # UK DEFRA / Carbon Trust estimates
    EQUIVALENCIES = {
        # Transportation
        # EPA: Average passenger vehicle emits ~400 grams CO2e per mile
        "miles_driven_car": 400.0,  # gCO2eq per mile (average passenger vehicle)
        "km_driven_car": 251,       # gCO2eq per km

        # Trees (carbon sequestration)
        "tree_year": 21772,       # gCO2eq sequestered per tree per year (avg)
        "tree_day": 59.6,         # gCO2eq sequestered per tree per day

        # Electronics
        # EPA: Average smartphone charge requires ~0.012 kWh
        # Global/US avg carbon intensity ~ 0.3-0.4 kg/kWh -> approx 5-8 grams per charge
        "smartphone_charge": 8.22,     # gCO2eq per full smartphone charge
        "laptop_charge": 47.0,         # gCO2eq per laptop charge (50Wh battery)
        "tablet_charge": 19.0,         # gCO2eq per tablet charge

        # Lighting
        "led_bulb_hour": 9.0,          # gCO2eq per hour (10W LED bulb)
        "incandescent_hour": 45.0,     # gCO2eq per hour (60W incandescent)

        # Streaming & Entertainment
        # Carbon Trust (Europe): 1 hour of video streaming (TV/Laptop) is approx 55g CO2e
        "streaming_hour": 55.0,        # gCO2eq per hour of HD video streaming

        # UK Specific
        # Beeco/Carbon Footprint Ltd: Boiling 1 liter of water in electric kettle
        "kettle_boil": 70.0,           # gCO2eq per liter boiled

        # Fuel
        "kg_coal_burned": 2419,        # gCO2eq per kg of coal burned
        "liter_gasoline": 2392,        # gCO2eq per liter of gasoline
        "gallon_gasoline": 8887,       # gCO2eq per gallon of gasoline

        # Food
        "kg_beef": 27000,              # gCO2eq per kg of beef
        "kg_chicken": 6900,            # gCO2eq per kg of chicken
        "kg_cheese": 13500,            # gCO2eq per kg of cheese

        # Other
        "plastic_bottle": 82.8,        # gCO2eq per plastic water bottle
        "aluminum_can": 170,           # gCO2eq per aluminum can
    }

    def __init__(self):
        """Initialize calculator with standard equivalency factors."""
        pass

    def calculate_equivalencies(self, gco2eq: float) -> Dict[str, Any]:
        """
        Calculate all equivalencies for a given amount of CO2 emissions.

        Args:
            gco2eq: Carbon emissions in grams of CO2 equivalent

        Returns:
            Dictionary of equivalencies with human-readable descriptions
        """
        if gco2eq <= 0:
            return {
                "total_gco2eq": 0,
                "equivalencies": {}
            }

        equivalencies = {}

        # Transportation
        equivalencies["miles_driven"] = {
            "value": gco2eq / self.EQUIVALENCIES["miles_driven_car"],
            "unit": "miles",
            "description": "Miles driven in an average passenger vehicle"
        }

        equivalencies["km_driven"] = {
            "value": gco2eq / self.EQUIVALENCIES["km_driven_car"],
            "unit": "kilometers",
            "description": "Kilometers driven in an average passenger vehicle"
        }

        # Trees
        equivalencies["trees_year"] = {
            "value": gco2eq / self.EQUIVALENCIES["tree_year"],
            "unit": "trees",
            "description": "Trees needed for one year to offset emissions"
        }

        equivalencies["trees_day"] = {
            "value": gco2eq / self.EQUIVALENCIES["tree_day"],
            "unit": "tree-days",
            "description": "Trees needed for one day to offset emissions"
        }

        # Electronics
        equivalencies["smartphone_charges"] = {
            "value": gco2eq / self.EQUIVALENCIES["smartphone_charge"],
            "unit": "charges",
            "description": "Smartphone battery charges (full cycle)"
        }

        equivalencies["laptop_charges"] = {
            "value": gco2eq / self.EQUIVALENCIES["laptop_charge"],
            "unit": "charges",
            "description": "Laptop battery charges (full cycle)"
        }

        # Lighting
        equivalencies["led_hours"] = {
            "value": gco2eq / self.EQUIVALENCIES["led_bulb_hour"],
            "unit": "hours",
            "description": "Hours of 10W LED light bulb usage"
        }

        # Streaming & UK Specific
        equivalencies["streaming_hours"] = {
            "value": gco2eq / self.EQUIVALENCIES["streaming_hour"],
            "unit": "hours",
            "description": "Hours of HD video streaming (Netflix, etc.)"
        }

        equivalencies["kettles_boiled"] = {
            "value": gco2eq / self.EQUIVALENCIES["kettle_boil"],
            "unit": "liters",
            "description": "Liters of water boiled in an electric kettle"
        }

        # Fuel
        equivalencies["kg_coal"] = {
            "value": gco2eq / self.EQUIVALENCIES["kg_coal_burned"],
            "unit": "kg",
            "description": "Kilograms of coal burned"
        }

        equivalencies["liters_gasoline"] = {
            "value": gco2eq / self.EQUIVALENCIES["liter_gasoline"],
            "unit": "liters",
            "description": "Liters of gasoline consumed"
        }

        # Waste
        equivalencies["plastic_bottles"] = {
            "value": gco2eq / self.EQUIVALENCIES["plastic_bottle"],
            "unit": "bottles",
            "description": "Plastic water bottles (500ml) produced"
        }

        equivalencies["aluminum_cans"] = {
            "value": gco2eq / self.EQUIVALENCIES["aluminum_can"],
            "unit": "cans",
            "description": "Aluminum cans (330ml) produced"
        }

        return {
            "total_gco2eq": gco2eq,
            "equivalencies": equivalencies
        }

    def get_top_equivalencies(
        self,
        gco2eq: float,
        count: int = 5
    ) -> Dict[str, Any]:
        """
        Get the most relatable equivalencies (values closest to 1-100 range).

        Args:
            gco2eq: Carbon emissions in grams of CO2 equivalent
            count: Number of top equivalencies to return

        Returns:
            Dictionary with the most relatable equivalencies
        """
        all_equivs = self.calculate_equivalencies(gco2eq)

        if not all_equivs["equivalencies"]:
            return all_equivs

        # Score each equivalency by how close it is to the ideal range (1-100)
        scored = []
        for key, equiv in all_equivs["equivalencies"].items():
            value = equiv["value"]
            # Prefer values between 1 and 100
            if value < 1:
                score = value  # Favor values closer to 1
            elif value <= 100:
                score = 1000  # Perfect range
            else:
                score = 100 / value  # Penalize very large values

            scored.append((score, key, equiv))

        # Sort by score (descending) and take top N
        scored.sort(reverse=True)
        top = scored[:count]

        top_equivalencies = {
            "total_gco2eq": gco2eq,
            "top_equivalencies": {
                key: equiv for _, key, equiv in top
            }
        }

        return top_equivalencies

    def format_equivalency(self, equivalency: Dict[str, Any]) -> str:
        """
        Format an equivalency as a human-readable string.

        Args:
            equivalency: Equivalency dictionary with value, unit, and description

        Returns:
            Formatted string
        """
        value = equivalency["value"]
        unit = equivalency["unit"]
        description = equivalency["description"]

        # Format value with appropriate precision
        if value < 0.01:
            value_str = f"{value:.4f}"
        elif value < 1:
            value_str = f"{value:.2f}"
        elif value < 10:
            value_str = f"{value:.1f}"
        else:
            value_str = f"{value:.0f}"

        return f"{value_str} {unit} - {description}"

    def format_all_equivalencies(self, gco2eq: float) -> str:
        """
        Format all equivalencies as a multi-line string.

        Args:
            gco2eq: Carbon emissions in grams of CO2 equivalent

        Returns:
            Formatted multi-line string
        """
        result = self.calculate_equivalencies(gco2eq)
        lines = [f"Carbon Emissions: {result['total_gco2eq']:.2f} gCO2eq\n"]
        lines.append("Equivalencies:")

        for key, equiv in result["equivalencies"].items():
            lines.append(f"  - {self.format_equivalency(equiv)}")

        return "\n".join(lines)


# Example Usage
if __name__ == "__main__":
    calculator = CarbonEquivalencyCalculator()

    # Example: 1000 gCO2eq (1 kg of CO2)
    print("=== Example 1: 1000 gCO2eq ===")
    equivalencies = calculator.calculate_equivalencies(1000)
    print(f"Total: {equivalencies['total_gco2eq']} gCO2eq\n")

    for key, equiv in equivalencies["equivalencies"].items():
        print(calculator.format_equivalency(equiv))

    # Example: Top 5 most relatable equivalencies
    print("\n=== Example 2: Top 5 Equivalencies for 5000 gCO2eq ===")
    top = calculator.get_top_equivalencies(5000, count=5)
    print(f"Total: {top['total_gco2eq']} gCO2eq\n")

    for key, equiv in top["top_equivalencies"].items():
        print(calculator.format_equivalency(equiv))

    # Example: Formatted output
    print("\n=== Example 3: Formatted Output ===")
    print(calculator.format_all_equivalencies(2500))
