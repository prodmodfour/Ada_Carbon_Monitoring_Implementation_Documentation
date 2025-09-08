# Workspace System — Quick Guide

This note explains how the **workspace** metrics are collected, stored, and displayed for each site (**clf**, **isis**, **diamond**).

---

## What it does

* A management command ('get_active_workspaces') queries the existing node_cpu_seconds_total parquet to find hosts that were active in the last hour that exists in that parquet:

  * Find **active hosts** (`up == 1`) for the site.
  * Get **start time** from `node_boot_time_seconds` (used as the workspace’s `started_at`). This data is gained by querying the prometheus database
  * Use the existing node_cpu_seconds_total parquet to find the idle and busy total for each host.
 
  * At the same time, it fetches current **carbon intensity** (gCO₂/kWh) from the **GB Carbon Intensity API**.
  * It estimates kilowatt-hours and carbon foorprint of both idle and busy usage. It saves these in a sqllite db, to be queried later in a django view in order to populate Workspace models. It estimates in the same manner used in the calculate_project_usage and calculate_project_footprint commands.

## Where the data shows up

* The **Analysis** page (`/analysis/<site>/`) reads from the `Workspace` table and renders the existing cards.
* Each card shows totals (kWh, kgCO₂e). There will be a circle that flashes next to these totals to indicate that they are live values but they won't actually be live as this is a mockup.
* Each card displays a doughnut graph comparing idle and busy usage.






