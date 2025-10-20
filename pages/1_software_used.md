---
title: Software Used
nav_order: 3
nav_exclude: false     
---

# APIs
## Carbon Intensity API


The [Carbon Intensity API](https://carbon-intensity.github.io/api-definitions/#carbon-intensity-api-v2-0-0) provides real-time and historical data about the carbon intensity of electricity generation — that is, how much carbon dioxide (CO₂) is emitted to produce a unit of electricity (usually measured in grams of CO₂ per kilowatt-hour, gCO₂/kWh).

We use the [Carbon Intensity API](https://carbon-intensity.github.io/api-definitions/#carbon-intensity-api-v2-0-0) to get the carbon intensity of electricity in the south east region of England (Where the data centre that Ada runs on in). This is used to estimate the carbon footprint of our compute usage.

# Databases
## Prometheus
We use [Prometheus](https://prometheus.io/) to collect and store metrics from our compute clusters. Prometheus is a time-series database that is well-suited for storing metrics data.

[Prometheus](https://prometheus.io/) is an open-source monitoring system built around **time-series metrics**. It:

* **Scrapes (pulls)** metrics over HTTP from targets on a schedule.
* Stores them in a local **TSDB** with labels (key=value) for rich dimensional queries.
* Lets you query with **PromQL**.


### How node_exporter works (incl. on VMs)

`node_exporter` is the standard OS-level exporter for *nix systems.

* **Where it runs:** Inside each VM . It’s a single binary, usually run as a systemd service, non-root.
* **What it collects:** Host/VM metrics such as CPU, memory, disk, filesystems, network, load, interrupts, etc., primarily from **/proc** and **/sys** (plus optional collectors like `systemd`, `processes`, `textfile`).
* **How it exposes data:** An HTTP endpoint  that returns either  plaintext Prometheus metrics or JSON files (unverified).
* **How data gets to Prometheus:** Prometheus **pulls** from each VM’s node_exporter on a scrape interval (Potentially every 15 seconds, unverified).

### How do we pull data from Prometheus?
See [Prometheus Request Class] for more details.


## MongoDB
[MongoDB](https://www.mongodb.com/) is a document-oriented NoSQL database that stores data in flexible, JSON-like BSON documents instead of rows and tables. It’s schema-optional, so fields can differ across documents and evolve over time. MongoDB is used to store the qualitative data for each workspace, as opposed to quantiative metrics data which is stored in Prometheus.

The mongoDB database stores the user and group that each workspace belongs to. We match this qualitative data with the prometheus metrics by matching timestamps.
To see more details, refer to [Group Attribution] and [User Attribution].

## SQLite


[SQLite](https://www.sqlite.org/index.html) is a lightweight, serverless SQL database engine that stores an entire database in a single cross-platform file. It’s zero-configuration (no separate server process), fully ACID-compliant, and implements most of SQL.

We use [SQLite](https://www.sqlite.org/index.html) to store our usage data.

To see the structure of our database, refer to [Database Structure].

To see how we pull data from SQLite, refer to [SQLite Class].

# Programming Languages
## Python
We use [Python](https://www.python.org/) for our backend development. Python is a versatile and powerful programming language that is well-suited for web development and data analysis.

## JavaScript
We use [JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript) for our frontend development. JavaScript is a popular programming language that is used to create interactive web applications.
# Frontend
## Svelte
We use [Svelte](https://svelte.dev/) for our frontend development. Svelte is a modern JavaScript framework that allows us to create fast and efficient web applications.
## Chart.js
We use [Chart.js](https://www.chartjs.org/) to create interactive charts and graphs for our frontend. Chart.js is a simple and flexible JavaScript charting library.
# Backend
## Flask
We use [Flask](https://flask.palletsprojects.com/en/2.3.x/) for our backend development. Flask is a lightweight web framework that allows us to create RESTful APIs and web applications.
# Documentation
## Jekyll
We use [Jekyll](https://jekyllrb.com/) to create our documentation website. Jekyll is a static site generator that allows us to create fast and efficient websites using Markdown.
## Mermaid.js
We use [Mermaid.js](https://mermaid-js.github.io/mermaid/#/) to create diagrams for our documentation. Mermaid.js is a simple and powerful tool that allows us to create diagrams using a simple syntax.

