---
title: Database Structure
parent: Backend
nav_order: 1
---

# Database Structure

{: .warning }
> **Note:** The SQLite-based documentation in this section is **deprecated**. The current implementation uses MongoDB via `ada-db-interface`.

## Current Architecture (MongoDB)

The carbon monitoring system now uses the existing Ada MongoDB database through `ada-db-interface`. This avoids maintaining a separate database and integrates directly with the Ada platform's data.

### Key Collections

| Collection | Purpose |
|------------|---------|
| `workspaces` | Active and historical workspace records |
| `users` | User information (platform_name, uid, email, tag) |
| `groups` | Experiment/group records (RB numbers, training courses) |
| `hosts` | Host/machine information |
| `specifications` | Workspace specification definitions |

### Data Flow

```
Prometheus (CPU metrics)
    ↓
ada-carbon-monitoring-api (calculation)
    ↓
ada-db-interface (user/group attribution)
    ↓
MongoDB (workspace/user/group data)
```

### User/Group Attribution

Attribution works by matching:
1. **Timestamp**: When did the CPU usage occur?
2. **Hostname**: Which workspace was using the CPU?
3. **Workspace ownership**: Who owned that workspace at that time?

See [User Attribution](../usage_estimation_methods/user_attribution.html) for details.

## Deprecated: SQLite Documentation

The following pages document the old SQLite-based design and are kept for reference only:

- [SQL Tables Guide](sql_tables_guide.html) - Deprecated
- [SQL Table Recipes](sql_table_recipes.html) - Deprecated
- [ERD](erd.html) - Deprecated
- [Dependency Diagram](dependency_diagram.html) - Deprecated
