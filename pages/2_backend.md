---
title: Backend
nav_order: 4    
nav_exclude: false     
---

# Database Structure
# Database Classes
## Prometheus Request Class
We have a Prometheus request class that handles requests to the Prometheus API. This class is used to download cpu_seconds data for a given time period.
## MongoDB Request Class
We have a MongoDB request class that handles requests to the MongoDB database. This class is used to store and retrieve estimated usage data.
## Carbon Intensity API Request Class
We have a Carbon Intensity API request class that handles requests to the Carbon Intensity API. This class is used to get the carbon intensity for a given time period.
## SQLite Class
We have a SQLite class that handles requests to the SQLite database. This class is used to store and retrieve machine averages data.

# Estimating Usage
We estimate usage by downloading cpu_seconds data from Prometheus. We then use machine averages to estimate energy usage and carbon footprint.

The purpose of this project is to provide the users of Ada with information that may lead them towards making greener choices in the future. 
We want users to know what impact they're having on the environment and what they can do reduce their impact.

To achieve this, there are three main variables that we need to make the user aware of.
These are:
* Electricity Usage
* Carbon Intensity
* Carbon Footprint

If users are aware of how their actions affect these three variables, they will be armed with the information necessary
to make the greenes choicest possible. They will be able to minimise their carbon footprint



## Electricity
We estimate electricity usage using machine averages. We multiply the cpu_seconds by the average power consumption of the machine (kW).
## Carbon Intensity
We get the carbon intensity from the Carbon Intensity API. This gives us the carbon intensity (gCo2eq per kwh) for a given time period.
## Carbon Footprint
We estimate carbon footprint using the Carbon Intensity API. We multiply the estimated kwh by the carbon intensity (gCo2eq per kwh).
# Workspace Tracking
We track workspaces by polling Prometheus for active hosts. We estimate their energy usage and carbon footprint using a power model and the Carbon Intensity API.
# Machine Averages
We store machine averages in a SQLite database. We use these averages to estimate energy usage and carbon footprint.
# Group Attribution
We attribute usage to groups based on the cloud_project_name. We store usage data for each group in a MongoDB database.
# User Attribution
We attribute usage to users based on the user label in Prometheus. We store usage data for each user in a MongoDB database.


# Data acquisition breakdown
We store:
* idle_cpu_seconds
* busy_cpu_seconds
* idle_kwh
* busy_kwh
* idle_gCo2eq
* busy_gCo2eq

We store data in a timeseries format for the last year. Data is stored in JSON files.

We store this data for each:
* Project
* Experiment
* Machine
* User

First, we download cpu_seconds data day by day. We make a request for an hours worth of cpu_seconds data.
This gives us a JSON object with a number of timeseries. We parse this object and save its data to various storage classes.
We have a usage storage class for each level of storage mentioned before. If the download fails, we store "failed" instead of a float.



We seperate data into hourly, monthly and yearly so that we can easily load this data to our graphs.

# EstimatedUsageDayEntry
```json
{
  "cloud_project_name": "project",
  "date": "DD_MM_YYYY",
  "timeseries": {
    "totals": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
      "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    },
    "00:00": {
      "all": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      },
        "ARTEMIS_MATLAB": {
        "busy_cpu_seconds_total": 0.0,
        "idle_cpu_seconds_total": 0.0,
        "busy_kwh": 0.0,
        "idle_kwh": 0.0,
        "busy_gCo2eq": 0.0,
        "idle_gCo2eq": 0.0
      }
    }
  }
}
```

## MachineMetrics
```json
{
  "machine_name": "Artemis Matlab",
  "metrics": {
    "energy_kwh": {
      "busy": {
        "average": 0.0
      },
      "idle": {
        "average": 0.0
      }
    },
    "carbon_gCo2eq": {
        "busy": {
            "average": 0.0
        },
        "idle": {
            "average": 0.0
      }
    }
  }
}
```

# ActiveWorkspace

* Stored in JSON
```json
{
    "instance": "instance="host-172-16-100-116.nubes.stfc.ac.uk:9100"",
    "machine_name": "Artemis (Matlab)",
    "busy_kwh": 0,
    "idle_kwh": 0,
    "busy_gCo2eq": 0,
    "idle_gCo2eq": 0
    "started_at": "2025-09-11T10:30:00Z"
}
```


# workspace tracking
# Workspace System — Quick Guide

This note explains how the **workspace** metrics are collected, stored, and displayed for each site (**clf**, **isis**, **diamond**).

---

## What it does

* Every minute, a poller (`sync_workspaces` management command) queries **Prometheus** to:

  * Find **active hosts** (`up == 1`) for the site.
  * Get **start time** from `node_boot_time_seconds` (used as the workspace’s `started_at`).
  * Compute **idle fraction** from CPU: `rate(node_cpu_seconds_total{mode="idle"}[1m]) / rate(node_cpu_seconds_total[1m])`.
  * Estimate **cores** and **memory activity** (Active / MemTotal).
* At the same time, it fetches current **carbon intensity** (gCO₂/kWh) from the **GB Carbon Intensity API**.
* It estimates per‑minute **energy** for each host, splits it into **busy vs idle**, converts to **kgCO₂e**, and stores everything in the `Workspace` row.

## Where the data shows up

* The **Analysis** page (`/analysis/<site>/`) reads from the `Workspace` table and renders the existing cards.
* Each card shows totals (kWh, kgCO₂e) and a live **Idle Use** ticker based on stored idle energy.

## How the numbers are calculated (per host)

* **Idle fraction** = idle CPU time ÷ total CPU time over the last minute.
* **Power model (W)** per minute:

  * `CPU = cores × cpu_tdp_w × (1 − idle_fraction)`
  * `RAM = ram_w × mem_active_ratio`
  * `Other = other_w`
  * `Watts = CPU + RAM + Other`
* **Energy (kWh)** per minute: `Watts / 1000 × (60 / 3600)`
* **Split**: `busy_kWh = kWh × (1 − idle_fraction)`; `idle_kWh = kWh × idle_fraction`
* **Emissions (kgCO₂e)**: `kWh × (CI_g_per_kWh / 1000)`
* **Runtime seconds** only increases with the **busy** portion.

## How to run

1. Ensure `PROMETHEUS_URL` is set in Django settings.
2. Start the poller (looping):

   ```bash
   python manage.py sync_workspaces --sleep 60
   ```

   Or run one cycle:

   ```bash
   python manage.py sync_workspaces --once
   ```
3. Start the web app:

   ```bash
   python manage.py runserver
   ```
4. Open: `/analysis/clf/`, `/analysis/isis/`, `/analysis/diamond/`.

## Configuration knobs (in the command)

* **Site mapping** → Prom label: `clf/isis/diamond → cloud_project_name` values.
* **Power model**: `cpu_tdp_w`, `ram_w`, `other_w` 
* **Carbon intensity**: fetched live (cached \~5 minutes); fallback used if API is down.




