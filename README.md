# Ada Carbon Monitoring Implementation Documentation

This repository documents the implementation of carbon monitoring for the Ada platform (https://ada.stfc.ac.uk/).

**View the documentation:** https://prodmodfour.github.io/Ada_Carbon_Monitoring_Implementation_Documentation/

## Current Status (January 2026)

The carbon monitoring system is **fully implemented** and ready for deployment.

### Implementation Complete

| Component | Status | Description |
|-----------|--------|-------------|
| Backend API | Complete | `ada-carbon-monitoring-api` - FastAPI service |
| API Integration | Complete | `ada-api` proxies carbon endpoints |
| Frontend UI | Complete | Svelte components in `ada-ui` |
| User Attribution | Complete | Track carbon by workspace owner |
| Group Attribution | Complete | Track carbon by cloud_project + machine_name |
| Documentation | Complete | This repository |

### Branch Structure

**ada-ui:**
| Branch | Purpose |
|--------|---------|
| `carbon-labs-platform` | Production - Carbon dashboard in Labs sidebar |
| `carbon-labs-demo` | Demo mode with fake data indicator |

**ada-carbon-monitoring-api:**
| Branch | Purpose |
|--------|---------|
| `carbon-labs-platform` | Production - Real Prometheus/MongoDB |
| `carbon-labs-demo` | Demo mode with fake data enabled |

### Quick Start

```bash
# Clone and run ada-carbon-monitoring-api
cd ada-carbon-monitoring-api
git checkout carbon-labs-platform
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8000

# Clone and run ada-ui
cd ada-ui
git checkout carbon-labs-platform
npm install
npm run dev  # Runs on http://localhost:5173
```

### Architecture

```
ada-ui (Svelte)
    |
    v
ada-api (FastAPI proxy)
    |
    v
ada-carbon-monitoring-api (FastAPI)
    |
    +---> Prometheus (CPU metrics)
    +---> MongoDB via ada-db-interface (user/workspace data)
    +---> UK Carbon Intensity API (grid carbon data)
```

## Related Repositories

| Repository | Purpose | Edit Policy |
|------------|---------|-------------|
| `ada-carbon-monitoring-api` | Carbon calculation backend | Free to edit |
| `ada-api` | Main Ada platform API | Only as necessary |
| `ada-ui` | Frontend Svelte components | Only as necessary |
| `ada-db-interface` | MongoDB interface | Only as necessary |

## Key Features

### Carbon Dashboard
- Summary cards (energy, carbon, workspaces, CPU time)
- Carbon intensity forecast with best 3-hour window
- GitHub-style year heatmap
- Stacked bar chart (busy/idle breakdown)
- Carbon equivalencies (miles driven, trees, etc.)

### API Endpoints
- `GET /carbon/intensity/current` - Current UK grid carbon intensity
- `GET /carbon/intensity/forecast` - 24/48 hour forecast
- `POST /carbon/calculate` - Calculate carbon from CPU seconds
- `GET /carbon/equivalencies/{gco2eq}` - Get equivalencies
- `GET /groups` - List all groups
- `GET /groups/{name}/summary` - Group carbon summary
- `GET /users/{username}/summary` - User carbon summary
- `GET /carbon/history` - Historical data for charts
- `GET /carbon/heatmap` - Heatmap data

### Carbon Calculation

```
Energy (kWh) = (12W × busy_seconds + 1W × idle_seconds) / 3,600,000
Carbon (gCO2eq) = Energy (kWh) × Carbon Intensity (gCO2/kWh)
```

## Documentation Structure

```
pages/
├── index.md                    # Introduction
├── 0_green_computing_basics.md # Carbon concepts
├── 1_software_used.md          # Tech stack
├── quickstart.md               # Getting started
├── api_reference.md            # API documentation
├── backend/
│   ├── 2_backend.md            # Backend overview
│   ├── database_structure/     # MongoDB structure
│   └── usage_estimation_methods/
│       ├── electricity.md      # kWh calculation
│       ├── carbon_footprint.md # CO2 calculation
│       ├── user_attribution.md # User tracking
│       └── group_attribution.md # Group tracking
└── frontend/
    └── 3_frontend.md           # Svelte components
```

## What is Carbon Monitoring?

Carbon monitoring systems:
1. Determine how much CO2 (or CO2 equivalent) was released by computing workloads
2. Collect that data over time
3. Display it to users with actionable insights

## What is the Ada Platform?

Ada is a service for members of STFC (https://www.ukri.org/councils/stfc/) providing:
- Virtual machines powered by the R86 data centre
- Remote data analysis for ISIS Neutron and Muon Source
- Workspaces for CLF (Central Laser Facility)
- Training environments

Used by scientists for computationally intensive workloads and accessing pre-installed scientific software.
