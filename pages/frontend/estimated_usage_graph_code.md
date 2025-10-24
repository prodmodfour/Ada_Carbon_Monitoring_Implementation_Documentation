---
title: Estimated Usage Graph
parent: Frontend
nav_order: 2
---

# Todo
* Add explanations
* Figure out how to serve interactive example on github pages

# Svelte Code

```ts
<script>
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';
  import { page } from '$app/stores';

  let chartCanvas;
  let chartInstance;

  // Reactive values controlling the UI
  let dataType = 'electricity'; // 'electricity' | 'carbon'
  let timeView = 'day';         // 'day' | 'month' | 'year'
  let selectedDate = '';
  let selectedMonth = '';
  let selectedYear = '';

  // Derived values from the URL parameters
  $: scope = $page.params.scope;
  $: entityName = $page.params.name;

  /**
   * Build a human readable title for the chart
   */
  function buildTitle() {
    const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
    let titleDate = '';
    if (timeView === 'day') {
      titleDate = ` for ${selectedDate}`;
    } else if (timeView === 'month') {
      const [y, m] = selectedMonth.split('-');
      // Construct a date on the second of the month to get the month name
      const date = new Date(`${selectedMonth}-02`);
      const monthName = date.toLocaleString('default', { month: 'long' });
      titleDate = ` for ${monthName} ${y}`;
    } else {
      titleDate = ` for ${selectedYear}`;
    }
    // Use the entityName where provided, otherwise fall back to scope
    const namePart = entityName || scope;
    return `${cap(dataType)} Usage - ${cap(timeView)} View for ${namePart}${titleDate}`;
  }

  /**
   * Determine the y‑axis title based on the chosen data type
   */
  function getYAxisTitle() {
    return dataType === 'electricity' ? 'Usage (kWh)' : 'Usage (gCO2eq)';
  }

  /**
   * Fetch aggregated usage data from the server.  The API endpoint is built
   * using the current scope and name from the URL.  Query parameters
   * control the time view, date/month/year value and the metric type.
   */
  async function fetchChartData() {
    const value =
      timeView === 'day'
        ? selectedDate
        : timeView === 'month'
        ? selectedMonth
        : selectedYear;
    const url = `/api/usage/${encodeURIComponent(scope)}/${encodeURIComponent(
      entityName
    )}?view=${encodeURIComponent(timeView)}&value=${encodeURIComponent(
      value
    )}&metric=${encodeURIComponent(dataType)}`;
    const res = await fetch(url);
    if (!res.ok) {
      console.error('Failed to fetch chart data', await res.text());
      return null;
    }
    return await res.json();
  }

  /**
   * Render the bar chart using Chart.js.  This function will destroy any
   * existing chart instance before creating a new one.  Chart data and
   * options are constructed from the API response and the current state.
   */
  async function renderChart() {
    const chartData = await fetchChartData();
    if (!chartData) return;
    const ctx = chartCanvas.getContext('2d');
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: buildTitle(),
            font: { size: 20 },
            padding: { top: 10, bottom: 30 }
          },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: { stacked: true },
          y: {
            stacked: true,
            beginAtZero: true,
            title: { display: true, text: getYAxisTitle() }
          }
        }
      }
    });
  }

  /**
   * Initialise date selectors on mount and render the initial chart.  The
   * defaults reflect the current day, month and year in the browser’s
   * timezone.  Users can override these via the pickers.
   */
  onMount(() => {
    const now = new Date();
    selectedDate = now.toISOString().slice(0, 10);
    selectedMonth = now.toISOString().slice(0, 7);
    selectedYear = now.toISOString().slice(0, 4);
    renderChart();
  });

  // Handlers for UI interactions.  Each updates the appropriate state and
  // triggers a re-render of the chart.
  function handleDataTypeChange(type) {
    dataType = type;
    renderChart();
  }
  function handleTimeViewChange(view) {
    timeView = view;
    renderChart();
  }
  function handleDateChange(event) {
    selectedDate = event.target.value;
    renderChart();
  }
  function handleMonthChange(event) {
    selectedMonth = event.target.value;
    renderChart();
  }
  function handleYearChange(event) {
    selectedYear = event.target.value;
    renderChart();
  }
</script>

<!-- Main container replicating the structure of the original HTML.  The
     responsive grid and form elements are styled using Tailwind CSS loaded
     via the CDN in the layout. -->
<div class="bg-gray-100 min-h-screen p-4 sm:p-6 md:p-8 font-sans">
  <div class="max-w-7xl mx-auto bg-white rounded-2xl shadow-lg p-4 sm:p-6">
    <h1 class="text-2xl sm:text-3xl font-bold text-gray-800 mb-6 text-center">
      {entityName || scope} Estimated Usage
    </h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 items-end">
      <!-- Data Type Tabs -->
      <div class="flex flex-col gap-2">
        <label class="text-sm font-medium text-gray-700">Data Type</label>
        <div class="flex bg-gray-200 rounded-lg p-1">
          <button
            on:click={() => handleDataTypeChange('electricity')}
            class="tab-btn w-full text-center px-4 py-2 rounded-md transition-colors duration-300 ease-in-out"
            class:bg-white={dataType === 'electricity'}
            class:shadow-md={dataType === 'electricity'}
            class:text-blue-600={dataType === 'electricity'}
            class:font-semibold={dataType === 'electricity'}
            class:text-gray-600={dataType !== 'electricity'}
            class:hover:bg-gray-300={dataType !== 'electricity'}
          >
            Electricity
          </button>
          <button
            on:click={() => handleDataTypeChange('carbon')}
            class="tab-btn w-full text-center px-4 py-2 rounded-md transition-colors duration-300 ease-in-out"
            class:bg-white={dataType === 'carbon'}
            class:shadow-md={dataType === 'carbon'}
            class:text-blue-600={dataType === 'carbon'}
            class:font-semibold={dataType === 'carbon'}
            class:text-gray-600={dataType !== 'carbon'}
            class:hover:bg-gray-300={dataType !== 'carbon'}
          >
            Carbon
          </button>
        </div>
      </div>

      <!-- Time View Tabs -->
      <div class="flex flex-col gap-2">
        <label class="text-sm font-medium text-gray-700">Time View</label>
        <div class="flex bg-gray-200 rounded-lg p-1">
          <button
            on:click={() => handleTimeViewChange('day')}
            class="tab-btn w-full text-center px-4 py-2 rounded-md transition-colors duration-300 ease-in-out"
            class:bg-white={timeView === 'day'}
            class:shadow-md={timeView === 'day'}
            class:text-blue-600={timeView === 'day'}
            class:font-semibold={timeView === 'day'}
            class:text-gray-600={timeView !== 'day'}
            class:hover:bg-gray-300={timeView !== 'day'}
          >
            Day
          </button>
          <button
            on:click={() => handleTimeViewChange('month')}
            class="tab-btn w-full text-center px-4 py-2 rounded-md transition-colors duration-300 ease-in-out"
            class:bg-white={timeView === 'month'}
            class:shadow-md={timeView === 'month'}
            class:text-blue-600={timeView === 'month'}
            class:font-semibold={timeView === 'month'}
            class:text-gray-600={timeView !== 'month'}
            class:hover:bg-gray-300={timeView !== 'month'}
          >
            Month
          </button>
          <button
            on:click={() => handleTimeViewChange('year')}
            class="tab-btn w-full text-center px-4 py-2 rounded-md transition-colors duration-300 ease-in-out"
            class:bg-white={timeView === 'year'}
            class:shadow-md={timeView === 'year'}
            class:text-blue-600={timeView === 'year'}
            class:font-semibold={timeView === 'year'}
            class:text-gray-600={timeView !== 'year'}
            class:hover:bg-gray-300={timeView !== 'year'}
          >
            Year
          </button>
        </div>
      </div>

      <!-- Date/Month/Year pickers -->
      <div class="flex flex-col gap-2">
        {#if timeView === 'day'}
          <label for="day-select" class="text-sm font-medium text-gray-700">
            Select Day
          </label>
          <input
            type="date"
            id="day-select"
            class="w-full p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            bind:value={selectedDate}
            on:change={handleDateChange}
          />
        {:else if timeView === 'month'}
          <label for="month-select" class="text-sm font-medium text-gray-700">
            Select Month
          </label>
          <input
            type="month"
            id="month-select"
            class="w-full p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            bind:value={selectedMonth}
            on:change={handleMonthChange}
          />
        {:else}
          <label for="year-input" class="text-sm font-medium text-gray-700">
            Year
          </label>
          <input
            type="number"
            id="year-input"
            class="w-full p-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            bind:value={selectedYear}
            on:change={handleYearChange}
          />
        {/if}
      </div>
    </div>
    <div class="relative h-[60vh]">
      <canvas bind:this={chartCanvas}></canvas>
    </div>
  </div>
</div>
```

# server.js

```javascript
import { execFile } from 'child_process';
import { promisify } from 'util';
import { json } from '@sveltejs/kit';

const execFileAsync = promisify(execFile);


export async function GET({ params, url }) {
  const { scope, name } = params;
  const view = url.searchParams.get('view') ?? 'day';
  // Determine default date values if none provided
  const now = new Date();
  // Format date into YYYY-MM-DD for day, YYYY-MM for month, YYYY for year
  let defaultValue;
  if (view === 'month') {
    defaultValue = now.toISOString().slice(0, 7);
  } else if (view === 'year') {
    defaultValue = now.toISOString().slice(0, 4);
  } else {
    defaultValue = now.toISOString().slice(0, 10);
  }
  const value = url.searchParams.get('value') ?? defaultValue;
  const metric = url.searchParams.get('metric') ?? 'electricity';

  try {
    // Build the argument list for the Python script.  Ensure strings are
    // provided for optional parameters to maintain positional arguments.
    const args = [
      scope,
      name || '',
      view,
      value,
      metric
    ];
    const { stdout } = await execFileAsync(
      'python3',
      ['scripts/query_usage.py', ...args],
      {
        cwd: process.cwd(),
        encoding: 'utf8',
      }
    );
    const data = JSON.parse(stdout);
    return json(data);
  } catch (err) {
    console.error('Error executing query_usage.py:', err);
    return json({ error: 'Failed to query usage' }, { status: 500 });
  }
}
```

# Python Helper

```python
import json
import os
import sqlite3
import sys
from datetime import datetime


def parse_args(argv):
    if len(argv) != 6:
        raise SystemExit(
            "Expected 5 arguments: <scope> <name> <view> <value> <metric>"
        )
    _, scope, name, view, value, metric = argv
    if scope not in {"ada", "project", "machine", "user"}:
        raise SystemExit(f"Unsupported scope '{scope}'")
    if view not in {"day", "month", "year"}:
        raise SystemExit(f"Unsupported view '{view}'")
    if metric not in {"electricity", "carbon"}:
        raise SystemExit(f"Unsupported metric '{metric}'")
    return scope, name, view, value, metric


def build_where(scope: str, name: str, cur: sqlite3.Cursor):
    """Return a SQL fragment to filter fact_usage rows for the requested scope.

    For the Ada scope no additional filtering is necessary.  For the other
    scopes the corresponding dimension table is queried to determine the
    primary key and the fact table is filtered accordingly.
    """
    if scope == "ada":
        return "scope='ada'", []
    elif scope == "project":
        return (
            "scope='project' AND project_id = (SELECT project_id FROM dim_project WHERE cloud_project_name = ?)",
            [name],
        )
    elif scope == "machine":
        return (
            "scope='machine' AND machine_id = (SELECT machine_id FROM dim_machine WHERE machine_name = ?)",
            [name],
        )
    elif scope == "user":
        return (
            "scope='user' AND user_id = ?",
            [name],
        )
    else:
        raise ValueError(f"Unsupported scope: {scope}")


def build_time_filter(view: str, value: str):
    """Return a SQL expression and parameter to constrain the time period."""
    if view == "day":
        # exact day, inclusive
        return "date(ts) = ?", [value]
    elif view == "month":
        return "strftime('%Y-%m', ts) = ?", [value]
    elif view == "year":
        return "strftime('%Y', ts) = ?", [value]
    else:
        raise ValueError(f"Unsupported view: {view}")


def build_grouping(view: str):
    """Return the expression to group the data and the expected label list."""
    if view == "day":
        # group by hour of day (00–23).  We return the two‑digit hour as the
        # grouping key and later add ":00" to display a nicely formatted label.
        return "strftime('%H', ts)", [f"{i:02d}" for i in range(24)]
    elif view == "month":
        # group by day of month (01–31)
        return "strftime('%d', ts)", [str(i).zfill(2) for i in range(1, 32)]
    elif view == "year":
        # group by month of year (01–12)
        return "strftime('%m', ts)", [str(i).zfill(2) for i in range(1, 13)]
    else:
        raise ValueError(f"Unsupported view: {view}")


def main():
    scope, name, view, value, metric = parse_args(sys.argv)

    # Determine the path to the database.  By default the database file lives
    # two directories above this script (at the repository root).  Adjust
    # `db_path` if you move the database elsewhere.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', '..', 'database.sqlite')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Compose filters
    where_clause, params = build_where(scope, name, cur)
    time_filter, time_params = build_time_filter(view, value)
    group_expr, all_labels = build_grouping(view)

    # Determine which columns to sum based on metric
    if metric == "electricity":
        busy_col = "busy_kwh"
        idle_col = "idle_kwh"
        unit = "kWh"
    else:
        busy_col = "busy_gCo2eq"
        idle_col = "idle_gCo2eq"
        unit = "gCO2eq"

    sql = f"""
        SELECT {group_expr} AS bucket,
               SUM({idle_col}) AS idle_val,
               SUM({busy_col}) AS busy_val
        FROM fact_usage
        WHERE {where_clause} AND {time_filter}
        GROUP BY bucket
        ORDER BY bucket
    """
    query_params = params + time_params
    cur.execute(sql, query_params)
    rows = cur.fetchall()

    # Build a mapping from bucket to values for easy lookup
    bucket_map = {row["bucket"]: row for row in rows}

    idle_list = []
    busy_list = []
    labels = []

    # Normalise labels and build the result arrays.  For day view we append
    # ":00" to the hour to display it as HH:00 on the x‑axis.  Keys used
    # to look up bucketed results are the raw hour/day/month strings.
    for label in all_labels:
        if view == "day":
            display_label = f"{label}:00"
            key = label
        else:
            display_label = label
            key = label
        labels.append(display_label)
        row = bucket_map.get(key)
        if row is not None and row["idle_val"] is not None:
            idle_list.append(row["idle_val"])
            busy_list.append(row["busy_val"])
        else:
            idle_list.append(0.0)
            busy_list.append(0.0)

    result = {
        "labels": labels,
        "datasets": [
            {
                "label": f"Idle ({unit})",
                "data": idle_list,
                # Colour choices roughly correspond to those in app.js
                "backgroundColor": "rgba(54, 162, 235, 0.6)" if metric == "electricity" else "rgba(75, 192, 192, 0.6)",
            },
            {
                "label": f"Busy ({unit})",
                "data": busy_list,
                "backgroundColor": "rgba(255, 99, 132, 0.6)" if metric == "electricity" else "rgba(255, 159, 64, 0.6)",
            },
        ],
    }
    json.dump(result, sys.stdout)
```