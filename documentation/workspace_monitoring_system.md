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
* **Power model**: `cpu_tdp_w`, `ram_w`, `other_w` (simple, easy to tune).
* **Carbon intensity**: fetched live (cached \~5 minutes); fallback used if API is down.

## Troubleshooting

* **No cards / empty page**: check the poller logs; verify Prometheus is reachable and hosts report `up==1` with the right `cloud_project_name`.
* **Zeros for energy/emissions**: hosts may be idle or counters missing; verify `node_exporter` metrics.
* **CI not changing**: confirm the Carbon Intensity API is reachable from the server.


