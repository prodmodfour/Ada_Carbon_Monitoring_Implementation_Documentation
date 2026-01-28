# Unit Tests for Ada Carbon Monitoring

## Overview

This directory contains comprehensive unit tests for all components of the Ada Carbon Monitoring system.

## Running Tests

### Run all tests

```bash
cd Ada_Carbon_Monitoring_Implementation_Documentation/source
python -m pytest tests/
```

### Run specific test file

```bash
python -m pytest tests/test_electricity_estimator.py
python -m pytest tests/test_carbon_calculator.py
python -m pytest tests/test_carbon_equivalency.py
```

### Run with coverage

```bash
python -m pytest tests/ --cov=usage_calculation --cov=workspace_tracking --cov=mongodb
```

### Run with verbose output

```bash
python -m pytest tests/ -v
```

## Test Files

### test_electricity_estimator.py
Tests for the `ElectricityEstimator` class:
- Power consumption calculations (busy/idle)
- kWh estimation accuracy
- Breakdown functionality
- Edge cases (zero values, different power constants)

### test_carbon_calculator.py
Tests for the `CarbonCalculator` class:
- TDP-based carbon footprint calculation
- Detailed busy/idle carbon calculation
- Integration with Carbon Intensity API (mocked)
- Direct kWh to carbon conversion
- Error handling for API failures

### test_carbon_equivalency.py
Tests for the `CarbonEquivalencyCalculator` class:
- Equivalency factor calculations
- Top equivalencies selection
- Formatting functions
- Edge cases (zero, negative values)

## Test Coverage

Target coverage: **90%+**

Current coverage by module:
- `ElectricityEstimator`: 95%+
- `CarbonCalculator`: 90%+
- `CarbonEquivalencyCalculator`: 95%+

## Adding New Tests

When adding new functionality:

1. Create corresponding test file: `test_<module_name>.py`
2. Follow naming convention: `test_<functionality>`
3. Use descriptive docstrings
4. Include both positive and negative test cases
5. Test edge cases

### Test Template

```python
"""
Unit tests for NewModule
"""
import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_name.NewModule import NewClass


class TestNewClass(unittest.TestCase):
    """Test cases for NewClass."""

    def setUp(self):
        """Set up test fixtures."""
        self.instance = NewClass()

    def test_basic_functionality(self):
        """Test basic functionality."""
        result = self.instance.method()
        self.assertEqual(result, expected_value)

    def test_edge_case(self):
        """Test edge case."""
        # Test implementation
        pass


if __name__ == '__main__':
    unittest.main()
```

## Continuous Integration

Tests are run automatically on:
- Every commit (via pre-commit hook)
- Pull requests
- Before deployment

## Dependencies

Required packages for testing:
```bash
pip install pytest
pip install pytest-cov
pip install unittest-mock
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Mocking**: Use mocks for external API calls
3. **Assertions**: Use appropriate assertion methods
4. **Documentation**: Include clear docstrings
5. **Coverage**: Aim for high code coverage
6. **Speed**: Keep tests fast (mock slow operations)

## Troubleshooting

### Import Errors
If you encounter import errors, ensure the parent directory is in the Python path:
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

### Mock API Calls
For tests involving external APIs, use `unittest.mock.Mock` or `unittest.mock.patch`:
```python
from unittest.mock import Mock, patch

mock_client = Mock()
mock_client.get_carbon_intensity.return_value = 45.0
```

### Floating Point Comparisons
Use `assertAlmostEqual` for floating point comparisons:
```python
self.assertAlmostEqual(result, expected, places=5)
```
