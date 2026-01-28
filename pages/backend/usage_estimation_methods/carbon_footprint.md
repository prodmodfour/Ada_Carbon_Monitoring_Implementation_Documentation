---
title: Carbon Footprint
parent: Usage Estimation
nav_order: 2
---

# Calculating Carbon Footprint

This page documents how the Ada Carbon Monitoring system calculates carbon footprint (gCO2eq) from electricity usage (kWh).

## Formula

```
Carbon Footprint (gCO2eq) = Electricity Usage (kWh) × Carbon Intensity (gCO2/kWh)
```

## Carbon Intensity

Carbon intensity measures the carbon dioxide emissions per unit of electricity generated. It varies based on:
- Time of day (lower at night, higher during peak demand)
- Weather (wind/solar generation vs fossil fuels)
- Season (heating demand in winter)

### UK Grid Carbon Intensity API

We use the [UK Carbon Intensity API](https://carbonintensity.org.uk/) for real-time data:

**Endpoint:** `https://api.carbonintensity.org.uk/intensity`

**Coverage:** Great Britain (England, Scotland, Wales)

**Update frequency:** Every 30 minutes

### Intensity Index

| Index | Range (gCO2/kWh) | Description |
|-------|------------------|-------------|
| Very Low | 0-50 | High renewable generation |
| Low | 50-100 | Good renewable mix |
| Moderate | 100-200 | Mixed generation |
| High | 200-300 | Higher fossil fuel use |
| Very High | 300+ | Peak demand, low renewables |

### Example Values (UK 2026)

| Time | Typical Intensity | Notes |
|------|-------------------|-------|
| 3 AM | 120 gCO2/kWh | Low demand, wind generation |
| 9 AM | 200 gCO2/kWh | Morning peak, gas plants online |
| 2 PM | 150 gCO2/kWh | Solar contributing |
| 6 PM | 250 gCO2/kWh | Evening peak demand |

## Implementation

### CarbonCalculator

```python
class CarbonCalculator:
    """Calculate carbon footprint from electricity usage."""

    def __init__(self, carbon_client: CarbonIntensityAPIClient):
        self.carbon_client = carbon_client

    def estimate_carbon_footprint(
        self,
        kwh: float,
        carbon_intensity_g_per_kwh: Optional[float] = None
    ) -> float:
        """
        Calculate carbon footprint in grams CO2 equivalent.

        Args:
            kwh: Electricity usage in kilowatt-hours
            carbon_intensity_g_per_kwh: Carbon intensity (fetches current if not provided)

        Returns:
            Carbon footprint in gCO2eq
        """
        if carbon_intensity_g_per_kwh is None:
            current = self.carbon_client.get_current_intensity()
            carbon_intensity_g_per_kwh = current["intensity"]

        return kwh * carbon_intensity_g_per_kwh

    def estimate_carbon_footprint_detailed(
        self,
        busy_cpu_seconds: float,
        idle_cpu_seconds: float,
        busy_power_w: float = 12.0,
        idle_power_w: float = 1.0,
        start_time: Optional[datetime] = None
    ) -> dict:
        """
        Calculate detailed carbon footprint with breakdown.

        Returns dict with electricity_kwh, carbon_gco2eq (busy/idle/total),
        and carbon_intensity.
        """
        # Calculate electricity
        busy_kwh = busy_power_w * busy_cpu_seconds / 3_600_000
        idle_kwh = idle_power_w * idle_cpu_seconds / 3_600_000
        total_kwh = busy_kwh + idle_kwh

        # Get carbon intensity
        if start_time:
            intensity = self.carbon_client.get_intensity_for_time(start_time)
        else:
            intensity = self.carbon_client.get_current_intensity()["intensity"]

        # Calculate carbon
        busy_gco2eq = busy_kwh * intensity
        idle_gco2eq = idle_kwh * intensity
        total_gco2eq = total_kwh * intensity

        return {
            "electricity_kwh": {
                "busy": busy_kwh,
                "idle": idle_kwh,
                "total": total_kwh
            },
            "carbon_gco2eq": {
                "busy": busy_gco2eq,
                "idle": idle_gco2eq,
                "total": total_gco2eq
            },
            "carbon_intensity_g_per_kwh": intensity
        }
```

**Location:** `ada-carbon-monitoring-api/src/calculators/carbon_calculator.py`

### CarbonIntensityAPIClient

```python
class CarbonIntensityAPIClient:
    """Client for UK Carbon Intensity API."""

    BASE_URL = "https://api.carbonintensity.org.uk"

    def get_current_intensity(self) -> dict:
        """Get current carbon intensity."""
        response = requests.get(f"{self.BASE_URL}/intensity")
        data = response.json()["data"][0]
        return {
            "intensity": data["intensity"]["actual"] or data["intensity"]["forecast"],
            "index": data["intensity"]["index"],
            "from": data["from"],
            "to": data["to"]
        }

    def get_forecast(self, hours: int = 24) -> dict:
        """Get carbon intensity forecast."""
        response = requests.get(f"{self.BASE_URL}/intensity/fw{hours}h")
        return {
            "forecasts": [
                {
                    "from_time": p["from"],
                    "to_time": p["to"],
                    "intensity_forecast": p["intensity"]["forecast"],
                    "intensity_index": p["intensity"]["index"]
                }
                for p in response.json()["data"]
            ]
        }

    def get_intensity_for_time(self, timestamp: datetime) -> float:
        """Get intensity for a specific time (averages two 30-min periods)."""
        # Rounds to nearest hour, queries both half-hour periods
        # Returns average of actual values
        ...
```

**Location:** `ada-carbon-monitoring-api/src/clients/carbon_intensity_client.py`

## Example Calculations

### Example 1: Low Carbon Time

Computing at 3 AM when intensity is low:

| Metric | Value |
|--------|-------|
| Electricity | 0.1 kWh |
| Carbon intensity | 100 gCO2/kWh |

```python
carbon = 0.1 × 100 = 10 gCO2eq
```

### Example 2: Peak Demand Time

Same computation at 6 PM when intensity is high:

| Metric | Value |
|--------|-------|
| Electricity | 0.1 kWh |
| Carbon intensity | 250 gCO2/kWh |

```python
carbon = 0.1 × 250 = 25 gCO2eq
```

**Result:** 2.5× more carbon for the same work!

### Example 3: Full Day Breakdown

An 8-hour job running through varying intensity:

| Period | kWh | Intensity | gCO2eq |
|--------|-----|-----------|--------|
| 9 AM - 12 PM | 0.03 | 200 | 6.0 |
| 12 PM - 3 PM | 0.03 | 150 | 4.5 |
| 3 PM - 6 PM | 0.03 | 220 | 6.6 |
| **Total** | **0.09** | **190 avg** | **17.1** |

## API Endpoint

```bash
POST /carbon/calculate
```

**Request:**
```json
{
  "busy_cpu_seconds": 1000,
  "idle_cpu_seconds": 5000,
  "busy_power_w": 12.0,
  "idle_power_w": 1.0
}
```

**Response:**
```json
{
  "electricity_kwh": {
    "busy": 0.00333,
    "idle": 0.00139,
    "total": 0.00472
  },
  "carbon_gco2eq": {
    "busy": 0.617,
    "idle": 0.257,
    "total": 0.874
  },
  "carbon_intensity_g_per_kwh": 185,
  "power_w": {
    "busy": 12.0,
    "idle": 1.0
  },
  "equivalencies": {
    "total_gco2eq": 0.874,
    "top_equivalencies": {...}
  }
}
```

## Time Shifting Opportunity

The carbon intensity forecast enables **time shifting** - scheduling work during low-carbon periods:

```python
forecast = carbon_client.get_forecast(hours=24)

# Find best 3-hour window
best_window = find_lowest_average_window(forecast, hours=3)
print(f"Best time to run: {best_window['start']} ({best_window['avg_intensity']} gCO2/kWh)")
```

This is visualized in the Carbon Intensity Forecast chart on the dashboard.

## Carbon Equivalencies

After calculating carbon footprint, we convert to relatable equivalencies:

```python
from src.calculators.carbon_equivalency import CarbonEquivalencyCalculator

calc = CarbonEquivalencyCalculator()
equivalencies = calc.get_top_equivalencies(total_gco2eq)

# Returns:
# {
#     "smartphone_charges": {"value": 0.11, "unit": "charges", "description": "..."},
#     "miles_driven": {"value": 0.002, "unit": "miles", "description": "..."},
#     ...
# }
```

→ See [Carbon Equivalencies](../../frontend/carbon_equivalents_example.html) for UI display

## Data Quality Notes

{: .note }
> **Prometheus data before March 2025** returns 0 due to label changes. Only data from March 2025 onwards is used for calculations.

{: .warning }
> If the Carbon Intensity API is unavailable, the system uses a **default intensity of 200 gCO2/kWh** (UK average) and marks the data as estimated.
