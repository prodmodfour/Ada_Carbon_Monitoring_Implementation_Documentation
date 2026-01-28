---
title: Quick Start
nav_order: 2
nav_exclude: false
---

# Quick Start Guide

Get the Ada Carbon Monitoring system running in minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Access to Prometheus server (or use fake data mode)
- Access to MongoDB (or use fake data mode)

## Option 1: Production Mode (Real Data)

### 1. Backend API

```bash
# Clone the repository
cd /path/to/ada-carbon-monitoring-api
git checkout carbon-labs-platform

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure (edit ada-carbon-monitoring-api.ini)
# Set PROMETHEUS_URL, MONGO_URI, etc.

# Run the API
python main.py
```

API runs at http://localhost:8000

### 2. Frontend UI

```bash
# Clone the repository
cd /path/to/ada-ui
git checkout carbon-labs-platform

# Install dependencies
npm install

# Run development server
npm run dev
```

UI runs at http://localhost:5173

### 3. Verify Installation

```bash
# Test API health
curl http://localhost:8000/health

# Test carbon intensity
curl http://localhost:8000/carbon/intensity/current

# Test calculation
curl -X POST http://localhost:8000/carbon/calculate \
  -H "Content-Type: application/json" \
  -d '{"busy_cpu_seconds": 1000, "idle_cpu_seconds": 5000}'
```

## Option 2: Demo Mode (Fake Data)

For testing without real Prometheus/MongoDB:

### 1. Backend API (Demo Mode)

```bash
cd /path/to/ada-carbon-monitoring-api
git checkout carbon-labs-demo

# The config already has fake data enabled:
# [TESTING]
# use_fake_prometheus = true
# use_fake_mongodb = true
# use_fake_carbon_intensity = true

python main.py
```

### 2. Frontend UI (Demo Mode)

```bash
cd /path/to/ada-ui
git checkout carbon-labs-demo

npm install
npm run dev
```

The demo mode shows an orange "Demo Mode" banner on the dashboard.

## Configuration Reference

### ada-carbon-monitoring-api.ini

```ini
[GENERAL]
version = 1.0.0
port = 8000
cors_allowed_origins = http://localhost:3000,http://localhost:5173

[PROMETHEUS]
url = https://your-prometheus-server/
timeout = 120

[REGISTER]
# ada-db-interface connection
hostname = http://localhost:5000
username = Admin
password = Password

[CARBON_INTENSITY]
api_url = https://api.carbonintensity.org.uk/intensity

[POWER]
busy_power_w = 12.0
idle_power_w = 1.0
cpu_tdp_w = 100.0

[TAGS]
labs = ISIS,CLF
training = TRAINING
generic = DEV,AI4Science

[TESTING]
use_fake_prometheus = false
use_fake_mongodb = false
use_fake_carbon_intensity = false
```

## Testing the Carbon Dashboard

1. Open http://localhost:5173 in your browser
2. Navigate to the Labs platform (ISIS or CLF)
3. Look for "Carbon" in the left sidebar
4. Click to view the Carbon Dashboard

### What You Should See

- **Summary Cards**: Energy (kWh), Carbon (gCO2eq), Workspaces, CPU time
- **Carbon Intensity Forecast**: Line chart with best 3-hour window highlighted
- **Stacked Bar Chart**: Busy vs idle breakdown
- **Heatmap**: GitHub-style year view
- **Equivalencies**: Miles driven, smartphone charges, etc.

## Common Issues

### API Returns 500 Error

Check the logs:
```bash
tail -f /tmp/ada-carbon-api.log
```

Common causes:
- Prometheus server unreachable
- MongoDB connection failed
- Invalid configuration

### No Data Showing

1. Verify Prometheus has data:
```bash
curl "http://your-prometheus/api/v1/query?query=node_cpu_seconds_total"
```

2. Check date range - data before March 2025 is ignored due to label changes

### CORS Errors in Browser

Update `cors_allowed_origins` in config to include your frontend URL.

## Next Steps

- [API Reference](api_reference.html) - All endpoints and parameters
- [Backend Architecture](backend/2_backend.html) - Detailed backend docs
- [Frontend Components](frontend/3_frontend.html) - Svelte component reference
