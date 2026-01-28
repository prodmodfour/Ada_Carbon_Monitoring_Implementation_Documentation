# Reference Implementations

This directory contains reference implementations that were used to develop the carbon monitoring system. The production code lives in `ada-carbon-monitoring-api`.

## Current Status

These files are **reference only**. The production implementation is in:
- **ada-carbon-monitoring-api** - Production FastAPI service
- **ada-ui** - Production Svelte components

## Directory Structure

```
source/
├── mongodb/                    # Reference MongoDB client
├── prometheus/                 # Reference Prometheus client
├── usage_calculation/          # Reference calculators
├── workspace_tracking/         # Reference workspace tracker
├── charts/                     # Reference chart implementations (vanilla JS)
└── tests/                      # Reference unit tests
```

## Production Equivalents

| Reference | Production Location |
|-----------|---------------------|
| mongodb/MongoDBClient.py | ada-carbon-monitoring-api/src/clients/mongodb_client.py |
| prometheus/PrometheusAPIClient.py | ada-carbon-monitoring-api/src/clients/prometheus_client.py |
| usage_calculation/ElectricityEstimator.py | ada-carbon-monitoring-api/src/calculators/electricity_estimator.py |
| usage_calculation/CarbonCalculator.py | ada-carbon-monitoring-api/src/calculators/carbon_calculator.py |
| usage_calculation/CarbonIntensityAPIClient.py | ada-carbon-monitoring-api/src/clients/carbon_intensity_client.py |
| workspace_tracking/WorkspaceTracker.py | ada-carbon-monitoring-api/src/models/workspace_tracker.py |
| workspace_tracking/WorkspaceUsageEntry.py | ada-carbon-monitoring-api/src/models/workspace_usage.py |
| workspace_tracking/CarbonEquivalencyCalculator.py | ada-carbon-monitoring-api/src/calculators/carbon_equivalency.py |
| charts/stacked_bar_chart/ | ada-ui/src/components/Carbon/CarbonStackedBarChart.svelte |
| charts/github_style/ | ada-ui/src/components/Carbon/CarbonHeatmap.svelte |

## Charts Reference

The `charts/` directory contains vanilla JavaScript implementations that can be used as reference for porting to other frameworks:

- `stacked_bar_chart/` - Busy/idle breakdown chart
- `github_style/` - Year heatmap (GitHub contribution style)
- `busy_only_bar_chart/` - Single dataset bar chart
- `busy_only_github_style/` - Busy-only heatmap

## Using Reference Code

These implementations can be used for:
1. Understanding the algorithms and data flow
2. Porting to other languages or frameworks
3. Testing and experimentation
4. Documentation examples

For production use, always refer to the ada-carbon-monitoring-api repository.
