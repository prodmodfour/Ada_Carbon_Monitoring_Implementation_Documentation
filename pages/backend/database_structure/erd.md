---
title: ERD
parent: Database Structure
nav_order: 2
---

# Todo
* Fix Mermaid ERD

# Entity Relationship Diagram
```mermaid
erDiagram
    %% Dimension tables
    dim_group {
        INTEGER group_id PK
        TEXT group_name UNIQUE
    }
    dim_user {
        TEXT user_id PK
        TEXT display_name
        INTEGER group_id FK
    }
    dim_project {
        INTEGER project_id PK
        TEXT cloud_project_name UNIQUE
    }
    dim_machine {
        INTEGER machine_id PK
        TEXT machine_name UNIQUE
    }
    dim_instance {
        INTEGER instance_id PK
        TEXT host
        INTEGER port
        TEXT raw_label
    }

    %% Many‑to‑many helper tables
    map_user_project {
        TEXT user_id PK
        INTEGER project_id PK
    }
    map_project_machine {
        INTEGER project_id PK
        INTEGER machine_id PK
    }

    %% Fact table with metrics
    fact_usage {
        INTEGER usage_id PK
        TEXT ts "ISO‑8601 timestamp"
        TEXT scope "ada|project|machine|user"
        INTEGER project_id FK
        INTEGER machine_id FK
        TEXT user_id FK
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
        REAL intensity_gCo2eq_kwh
    }

    %% Active workspaces
    active_workspace {
        INTEGER workspace_id PK
        INTEGER instance_id FK
        INTEGER machine_id FK
        TEXT user_id FK
        INTEGER project_id FK
        TEXT started_at "ISO‑8601 timestamp"
    }

    %% Derived views (treated as entities for completeness)
    v_ada_timeseries {
        TEXT ts
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
        REAL intensity_gCo2eq_kwh
    }
    v_project_timeseries {
        TEXT cloud_project_name
        TEXT ts
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
        REAL intensity_gCo2eq_kwh
    }
    v_machine_timeseries {
        TEXT machine_name
        TEXT ts
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
        REAL intensity_gCo2eq_kwh
    }
    v_user_timeseries {
        TEXT user_id
        TEXT ts
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
        REAL intensity_gCo2eq_kwh
    }
    v_project_totals {
        TEXT cloud_project_name
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
    }
    v_machine_totals {
        TEXT machine_name
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
    }
    v_group_totals {
        TEXT group_name
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
    }
    v_user_totals {
        TEXT user_id
        REAL busy_cpu_seconds_total
        REAL idle_cpu_seconds_total
        REAL busy_kwh
        REAL idle_kwh
        REAL busy_gCo2eq
        REAL idle_gCo2eq
    }
    v_project_averages {
        TEXT cloud_project_name
        REAL avg_busy_energy_kwh
        REAL avg_idle_energy_kwh
        REAL avg_busy_carbon_gCo2eq
        REAL avg_idle_carbon_gCo2eq
        REAL avg_intensity_gCo2eq_kwh
    }
    v_machine_averages {
        TEXT machine_name
        REAL avg_busy_energy_kwh
        REAL avg_idle_energy_kwh
        REAL avg_busy_carbon_gCo2eq
        REAL avg_idle_carbon_gCo2eq
        REAL avg_intensity_gCo2eq_kwh
    }
    v_group_averages {
        TEXT group_name
        REAL avg_busy_energy_kwh
        REAL avg_idle_energy_kwh
        REAL avg_busy_carbon_gCo2eq
        REAL avg_idle_carbon_gCo2eq
        REAL avg_intensity_gCo2eq_kwh
    }
    v_user_averages {
        TEXT user_id
        REAL avg_busy_energy_kwh
        REAL avg_idle_energy_kwh
        REAL avg_busy_carbon_gCo2eq
        REAL avg_idle_carbon_gCo2eq
        REAL avg_intensity_gCo2eq_kwh
    }

    %% Relationships between tables
    dim_group ||--o{ dim_user : "group_id"
    dim_user  ||--o{ map_user_project     : "user_id"
    dim_project ||--o{ map_user_project    : "project_id"
    dim_project ||--o{ map_project_machine : "project_id"
    dim_machine ||--o{ map_project_machine : "machine_id"
    dim_project ||--o{ fact_usage          : "project_id"
    dim_machine ||--o{ fact_usage          : "machine_id"
    dim_user  ||--o{ fact_usage          : "user_id"
    dim_instance ||--o{ active_workspace   : "instance_id"
    dim_machine   ||--o{ active_workspace   : "machine_id"
    dim_user      ||--o{ active_workspace   : "user_id"
    dim_project   ||--o{ active_workspace   : "project_id"

    %% Relationships for views (showing their derivation)
    fact_usage ||--o{ v_ada_timeseries    : "ts"
    fact_usage ||--o{ v_project_timeseries : "project_id"
    dim_project ||--o{ v_project_timeseries : "project_id"
    fact_usage ||--o{ v_machine_timeseries : "machine_id"
    dim_machine ||--o{ v_machine_timeseries : "machine_id"
    fact_usage ||--o{ v_user_timeseries    : "user_id"
    dim_user ||--o{ v_user_timeseries     : "user_id"

    fact_usage ||--o{ v_project_totals     : "project_id"
    dim_project ||--o{ v_project_totals    : "project_id"
    fact_usage ||--o{ v_machine_totals     : "machine_id"
    dim_machine ||--o{ v_machine_totals    : "machine_id"
    fact_usage ||--o{ v_group_totals       : "user_id"
    dim_user ||--o{ v_group_totals        : "user_id"
    dim_group ||--o{ v_group_totals       : "group_id"
    fact_usage ||--o{ v_user_totals        : "user_id"
    dim_user ||--o{ v_user_totals         : "user_id"

    fact_usage ||--o{ v_project_averages   : "project_id"
    dim_project ||--o{ v_project_averages  : "project_id"
    fact_usage ||--o{ v_machine_averages   : "machine_id"
    dim_machine ||--o{ v_machine_averages  : "machine_id"
    fact_usage ||--o{ v_group_averages     : "user_id"
    dim_user ||--o{ v_group_averages      : "user_id"
    dim_group ||--o{ v_group_averages     : "group_id"
    fact_usage ||--o{ v_user_averages      : "user_id"
    dim_user ||--o{ v_user_averages       : "user_id"
```