---
title: Carbon Intensity Forecast
parent: Frontend
nav_order: 1
---

# Todo
* Figure out how to display on github pages

# Carbon Intensity Forecast
We use the Carbon Intensity API to get a forecast of the carbon intensity of electricity in the UK. This is displayed as a line graph on the frontend.

```ts
<script lang="ts">
  import { onMount } from 'svelte';
  import { writable, get } from 'svelte/store';
  import type { Chart } from 'chart.js';

  // Range selection state
  const range = writable<'working' | '24h' | '48h' | 'custom'>('working');
  const customFrom = writable<string>('');
  const customTo = writable<string>('');

  // Chart related state
  let chart: Chart | null = null;
  let chartCanvas: HTMLCanvasElement;
  let chartJs: any;

  // Whether to display the help popover
  let showPopover = false;

  // Data arrays for the chart
  let labels: string[] = [];
  let intensities: number[] = [];
  let bestWindow: { start: number; end: number; avg: number } | null = null;
  let nowMarkerIndex: number | null = null;

  // Helper to load Chart.js only on the client
  async function loadChartJs() {
    if (!chartJs) {
      // Use UMD bundle via CDN to avoid local install if not available.
      const module = await import('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js');
      chartJs = module.default ?? module;
    }
  }

  // Compute the time range for the API request based on the selected option
  function computeRange() {
    const selection = get(range);
    const now = new Date();
    let start = new Date(now);
    let end = new Date(now);

    if (selection === 'working') {
      // Determine the day for the working window (08:00–17:00)
      const today = new Date();
      if (now.getHours() < 8) {
        // before 08:00 → today 08:00–17:00
        start = new Date(today);
        start.setHours(8, 0, 0, 0);
        end = new Date(today);
        end.setHours(17, 0, 0, 0);
      } else if (now.getHours() >= 17) {
        // after 17:00 → tomorrow 08:00–17:00
        const tomorrow = new Date(now);
        tomorrow.setDate(now.getDate() + 1);
        start = new Date(tomorrow);
        start.setHours(8, 0, 0, 0);
        end = new Date(tomorrow);
        end.setHours(17, 0, 0, 0);
      } else {
        // between 08:00 and 17:00 → now–17:00
        start = new Date(now);
        end = new Date(now);
        end.setHours(17, 0, 0, 0);
      }
    } else if (selection === '24h') {
      // Next 24 hours from now
      start = new Date(now);
      end = new Date(now.getTime() + 24 * 60 * 60 * 1000);
    } else if (selection === '48h') {
      // Next 48 hours from now
      start = new Date(now);
      end = new Date(now.getTime() + 48 * 60 * 60 * 1000);
    } else if (selection === 'custom') {
      // Custom range as provided by inputs. Convert local times to Date objects.
      const fromVal = get(customFrom);
      const toVal = get(customTo);
      if (fromVal) start = new Date(fromVal);
      if (toVal) end = new Date(toVal);
    }
    return { start, end };
  }

  // Fetch data from the Carbon Intensity API for the selected range
  async function fetchData() {
    const { start, end } = computeRange();
    // Construct ISO strings in UTC as required by the API (drop milliseconds)
    const isoStart = start.toISOString().slice(0, 19) + 'Z';
    const isoEnd = end.toISOString().slice(0, 19) + 'Z';
    try {
      const res = await fetch(`https://api.carbonintensity.org.uk/intensity/${isoStart}/${isoEnd}`);
      const json = await res.json();
      const data = json.data ?? [];
      labels = [];
      intensities = [];
      const now = new Date();
      nowMarkerIndex = null;
      // Populate labels and intensities arrays; choose forecast if available else actual
      data.forEach((item: any, idx: number) => {
        const fromTime = new Date(item.from);
        const toTime = new Date(item.to);
        const intensity = item.intensity.forecast ?? item.intensity.actual;
        // Format label as HH:MM
        const label = fromTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        labels.push(label);
        intensities.push(intensity);
        // Determine index of the current half-hour containing now
        if (fromTime <= now && now < toTime) {
          nowMarkerIndex = idx;
        }
      });
      computeBestWindow();
      updateChart();
    } catch (err) {
      console.error('Failed to fetch data', err);
    }
  }

  // Compute the best 3-hour window (6 consecutive points) with the lowest average intensity
  function computeBestWindow() {
    bestWindow = null;
    if (intensities.length < 6) return;
    let bestAvg = Infinity;
    let bestStart = 0;
    for (let i = 0; i <= intensities.length - 6; i++) {
      const slice = intensities.slice(i, i + 6);
      const sum = slice.reduce((a, b) => a + b, 0);
      const avg = sum / 6;
      if (avg < bestAvg) {
        bestAvg = avg;
        bestStart = i;
      }
    }
    bestWindow = { start: bestStart, end: bestStart + 5, avg: Math.round(bestAvg) };
  }

  // Create or update the Chart.js instance
  async function updateChart() {
    await loadChartJs();
    const ChartClass = chartJs.Chart;
    if (chart) {
      // Update existing chart datasets and labels
      chart.data.labels = labels;
      chart.data.datasets[0].data = intensities;
      chart.update();
    } else if (chartCanvas) {
      const ctx = chartCanvas.getContext('2d');
      chart = new ChartClass(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Carbon intensity (gCO₂/kWh)',
              data: intensities,
              borderColor: '#58a6ff',
              backgroundColor: '#58a6ff',
              pointRadius: 3,
              tension: 0.3,
              fill: false
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (context: any) => `${context.parsed.y} gCO₂/kWh`
              }
            }
          },
          scales: {
            x: {
              title: { display: false },
              grid: { display: false }
            },
            y: {
              title: { display: false },
              ticks: {
                callback: (value: any) => `${value}`
              }
            }
          }
        },
        plugins: [highlightPlugin, nowMarkerPlugin]
      });
    }
  }

  // Plugin to highlight the best 3-hour window with a light green rectangle
  const highlightPlugin = {
    id: 'highlightPlugin',
    beforeDatasetsDraw(chart: any, args: any, pluginOptions: any) {
      if (!bestWindow) return;
      const { ctx, chartArea: { left, right, top, bottom }, scales: { x } } = chart;
      const startIdx = bestWindow.start;
      const endIdx = bestWindow.end;
      // Compute pixel positions for the start and end of the highlight
      const startVal = chart.data.labels[startIdx];
      const endVal = chart.data.labels[endIdx];
      const xStart = x.getPixelForValue(startVal);
      const xEnd = x.getPixelForValue(endVal);
      ctx.save();
      ctx.fillStyle = 'rgba(165, 215, 146, 0.2)';
      ctx.fillRect(xStart, top, xEnd - xStart, bottom - top);
      ctx.restore();
    }
  };

  // Plugin to draw a dashed vertical line at the current time marker
  const nowMarkerPlugin = {
    id: 'nowMarkerPlugin',
    afterDraw(chart: any, args: any, pluginOptions: any) {
      if (nowMarkerIndex == null) return;
      const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
      const label = chart.data.labels[nowMarkerIndex];
      const xPos = x.getPixelForValue(label);
      ctx.save();
      ctx.strokeStyle = '#888';
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(xPos, top);
      ctx.lineTo(xPos, bottom);
      ctx.stroke();
      ctx.restore();
    }
  };

  // Fetch data whenever the selected range or custom dates change
  // When the selected range or custom times change, fetch new data
  $: {
    $range;
    $customFrom;
    $customTo;
    if (chartJs) {
      // Avoid running before Chart.js is loaded
      fetchData();
    }
  }

  // Initialize the chart on mount
  onMount(async () => {
    await loadChartJs();
    await fetchData();
  });
</script>

<style>
  .card {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 1rem;
    background-color: #ffffff;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }
  .title {
    font-weight: 600;
    font-size: 1.25rem;
    margin-bottom: 0.25rem;
  }
  .subtitle {
    color: #6b7280;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }
  .pill {
    border: 1px solid #d1d5db;
    border-radius: 9999px;
    padding: 0.25rem 0.75rem;
    margin-right: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    background-color: #f9fafb;
    transition: background-color 0.2s;
  }
  .pill.active {
    background-color: #2563eb;
    color: white;
    border-color: #2563eb;
  }
  .pill:hover:not(.active) {
    background-color: #f3f4f6;
  }
  .controls {
    margin-bottom: 1rem;
  }
  .chart-container {
    position: relative;
    height: 300px;
  }
  .best-window {
    font-size: 0.875rem;
    margin-top: 0.5rem;
    color: #374151;
  }
  .popover-btn {
    border: none;
    background: none;
    cursor: pointer;
    font-weight: bold;
    font-size: 1rem;
  }
  .popover {
    position: absolute;
    right: 0;
    top: 2rem;
    width: 280px;
    padding: 1rem;
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    box-shadow: 0 5px 10px rgba(0, 0, 0, 0.1);
    z-index: 10;
  }
  .popover h4 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
  }
  .popover ul {
    margin: 0;
    padding-left: 1rem;
    list-style-type: disc;
    font-size: 0.875rem;
    color: #374151;
  }
  .popover p {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.5rem;
  }
</style>

<div class="card">
  <div class="header" style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <div class="title">Carbon Intensity Forecast (GB)</div>
      <div class="subtitle">All times local. Source: GB Carbon Intensity API.</div>
    </div>
    <div style="position: relative;">
      <button class="popover-btn" on:click={() => showPopover = !showPopover}>?</button>
      {#if showPopover}
        <div class="popover">
          <h4>What am I seeing?</h4>
          <ul>
            <li><strong>Data:</strong> half-hourly <em>forecast</em> of GB grid carbon intensity (gCO₂/kWh).</li>
            <li><strong>Times:</strong> shown in your local time; the API provides UTC which we convert.</li>
            <li><strong>Ranges:</strong> Working day (08:00–17:00), next 24h, next 48h, or a custom range (capped at 48h since longer forecasts are less accurate).</li>
            <li><strong>Best 3‑hour window:</strong> the light green band marks the lowest contiguous 3 hours (6 half‑hour points) by average gCO₂/kWh.</li>
            <li><strong>Now marker:</strong> a dashed line appears if “now” falls in the selected range.</li>
            <li><strong>Working day rule:</strong> before 08:00 → today; after 17:00 → tomorrow (weekends included).</li>
          </ul>
          <p class="ci-popover-foot">Source: GB Carbon Intensity API.</p>
        </div>
      {/if}
    </div>
  </div>
  <div class="controls">
    <button
      class="pill { $range === 'working' ? 'active' : '' }"
      on:click={() => range.set('working')}
      title="08:00–17:00"
    >Working day (8:00–17:00)</button>
    <button
      class="pill { $range === '24h' ? 'active' : '' }"
      on:click={() => range.set('24h')}
    >Next 24 hours</button>
    <button
      class="pill { $range === '48h' ? 'active' : '' }"
      on:click={() => range.set('48h')}
    >Next 48 hours</button>
    <button
      class="pill { $range === 'custom' ? 'active' : '' }"
      on:click={() => range.set('custom')}
    >Custom</button>
    {#if $range === 'custom'}
      <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; align-items: center;">
        <label style="font-size: 0.875rem;">From
          <input type="datetime-local" bind:value={$customFrom}>
        </label>
        <label style="font-size: 0.875rem;">To
          <input type="datetime-local" bind:value={$customTo}>
        </label>
      </div>
    {/if}
  </div>
  <div class="chart-container">
    <canvas bind:this={chartCanvas}></canvas>
  </div>
  {#if bestWindow}
    <div class="best-window">
      Best 3h window: {labels[bestWindow.start]}–{labels[bestWindow.end]} (avg {bestWindow.avg} gCO₂/kWh)
    </div>
  {/if}
</div>
```