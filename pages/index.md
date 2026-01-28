---
layout: page
title: Introduction
nav_order: 1
nav_exclude: false
permalink: /
---

# Ada Carbon Monitoring Documentation

This documentation covers the implementation of carbon monitoring for the Ada platform.

**Ada Platform:** [https://ada.stfc.ac.uk/](https://ada.stfc.ac.uk/)

## Implementation Status

{: .highlight }
> **Status: Complete** - The carbon monitoring system is fully implemented and ready for deployment.

| Component | Status |
|-----------|--------|
| Backend API (`ada-carbon-monitoring-api`) | Complete |
| API Integration (`ada-api`) | Complete |
| Frontend UI (`ada-ui`) | Complete |
| User Attribution | Complete |
| Group Attribution | Complete |
| Documentation | Complete |

## Quick Links

- [Getting Started](quickstart.html) - Set up and run the system
- [API Reference](api_reference.html) - All API endpoints
- [Backend](backend/2_backend.html) - Backend architecture
- [Frontend](frontend/3_frontend.html) - Svelte components

## What is Carbon Monitoring?

Carbon monitoring systems:
1. **Measure** - Determine how much CO2 (or CO2 equivalent) was released by computing workloads
2. **Collect** - Store that data over time for analysis
3. **Display** - Show users their carbon footprint with actionable insights

## What is the Ada Platform?

The Ada platform is a service for members of [STFC](https://www.ukri.org/councils/stfc/), providing:
- Virtual machines powered by the R86 data centre at Rutherford Appleton Laboratory
- Remote data analysis for ISIS Neutron and Muon Source
- Workspaces for CLF (Central Laser Facility)
- Training environments for scientific computing

### Who Uses Ada?

Scientists from:
- **ISIS** - Neutron and muon research
- **CLF** - Laser physics research
- **Diamond** - Synchrotron research
- **Training** - Scientific computing courses

### What Are Workspaces Used For?

- Running computationally intensive analysis
- Accessing pre-installed scientific software
- Remote access to facility data

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        ada-ui                               │
│                   (Svelte Frontend)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │  Dashboard  │ │   Heatmap   │ │  Intensity Forecast │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ API calls
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                       ada-api                               │
│                  (FastAPI Proxy)                            │
└────────────────────────┬────────────────────────────────────┘
                         │ Proxy
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               ada-carbon-monitoring-api                     │
│                     (FastAPI)                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ Calculators │ │   Clients   │ │      Models         │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└───────┬─────────────────┬───────────────────┬───────────────┘
        │                 │                   │
        ▼                 ▼                   ▼
┌───────────────┐ ┌───────────────┐ ┌─────────────────────────┐
│  Prometheus   │ │   MongoDB     │ │  UK Carbon Intensity    │
│ (CPU metrics) │ │  (via ada-db) │ │        API              │
└───────────────┘ └───────────────┘ └─────────────────────────┘
```

## Key Features

### Carbon Dashboard
- **Summary Cards** - Energy (kWh), Carbon (gCO2eq), Workspaces, CPU time
- **Carbon Intensity Forecast** - UK grid forecast with best 3-hour window
- **Heatmap** - GitHub-style year view of daily carbon
- **Stacked Bar Chart** - Busy vs idle breakdown by day/month/year
- **Equivalencies** - Miles driven, smartphone charges, trees, etc.

### Attribution
- **User Attribution** - Track carbon by workspace owner
- **Group Attribution** - Track carbon by cloud project + machine type

### Carbon Calculation
```
Energy (kWh) = (12W × busy_seconds + 1W × idle_seconds) / 3,600,000
Carbon (gCO2eq) = Energy (kWh) × Carbon Intensity (gCO2/kWh)
```

## Documentation Sections

| Section | Content |
|---------|---------|
| [Green Computing Basics](0_green_computing_basics.html) | Carbon concepts and reduction methods |
| [Software Used](1_software_used.html) | Technology stack |
| [Backend](backend/2_backend.html) | API architecture and endpoints |
| [Frontend](frontend/3_frontend.html) | Svelte component reference |
| [API Reference](api_reference.html) | Complete API documentation |
