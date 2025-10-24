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
  %% === Dimension tables ===
  dim_group {
    int    group_id PK
    string group_name
  }

  dim_user {
    string user_id PK
    string display_name
    int    group_id FK
  }

  dim_project {
    int    project_id PK
    string cloud_project_name
  }

  dim_machine {
    int    machine_id PK
    string machine_name
  }

  dim_instance {
    int    instance_id PK
    string host
    int    port
    string raw_label
  }

  %% === Mapping tables (M:N helpers) ===
  map_user_project {
    string user_id PK FK
    int    project_id PK FK
  }

  map_project_machine {
    int    project_id PK FK
    int    machine_id PK FK
  }

  %% === Fact tables ===
  fact_usage {
    int    usage_id PK
    string ts
    string scope
    int    project_id FK
    int    machine_id FK
    string user_id   FK
    float  busy_cpu_seconds_total
    float  idle_cpu_seconds_total
    float  busy_kwh
    float  idle_kwh
    float  busy_gCo2eq
    float  idle_gCo2eq
    float  intensity_gCo2eq_kwh
  }

  active_workspace {
    int    workspace_id PK
    int    instance_id  FK
    int    machine_id   FK
    string user_id      FK
    int    project_id   FK
    string started_at
  }

  %% === Relationships ===
  dim_group   ||--o{ dim_user            : has_users
  dim_user    ||--o{ map_user_project    : maps
  dim_project ||--o{ map_user_project    : maps
  dim_project ||--o{ map_project_machine : maps
  dim_machine ||--o{ map_project_machine : maps

  dim_project ||--o{ fact_usage          : project_scope_rows
  dim_machine ||--o{ fact_usage          : machine_scope_rows
  dim_user    ||--o{ fact_usage          : user_scope_rows

  dim_instance ||--o{ active_workspace   : hosts
  dim_machine  ||--o{ active_workspace   : runs_on
  dim_user     ||--o{ active_workspace   : opened_by
  dim_project  ||--o{ active_workspace   : belongs_to
```