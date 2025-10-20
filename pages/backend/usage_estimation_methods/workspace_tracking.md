---
title: Workspace Tracking
parent: Usage Estimation
nav_order: 3
---

# Todo
* Explain how we poll prometheus to find active workspaces
* Explain how we get data of that workspace

# Workspace Tracking
We track workspaces by polling Prometheus for active hosts. We estimate their energy usage and carbon footprint using a power model and the Carbon Intensity API.