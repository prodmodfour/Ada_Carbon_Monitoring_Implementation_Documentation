---
title: Frontend
nav_order: 7
nav_exclude: false
---

# Frontend Components

The Ada UI uses Svelte components for carbon monitoring visualization. All components are located in `ada-ui/src/components/Carbon/`.

## Component Overview

| Component | Purpose |
|-----------|---------|
| `CarbonDashboard` | Main dashboard combining all carbon views |
| `CarbonIntensityForecast` | UK grid carbon intensity forecast chart |
| `CarbonEquivalencies` | Real-world carbon equivalencies display |
| `CarbonStackedBarChart` | Busy/idle usage breakdown chart |
| `CarbonHeatmap` | GitHub-style year heatmap |
| `WorkspaceCarbonUsage` | Per-workspace carbon tracking |
| `CarbonBadge` | Compact carbon indicator for workspace cards |

## Architecture

```
ada-ui (Svelte)
    │
    ├── src/components/Carbon/
    │   ├── CarbonDashboard.svelte      # Main dashboard
    │   ├── CarbonIntensityForecast.svelte  # Forecast chart
    │   ├── CarbonEquivalencies.svelte  # Equivalencies display
    │   ├── CarbonStackedBarChart.svelte # Stacked bar chart
    │   ├── CarbonHeatmap.svelte        # Year heatmap
    │   ├── WorkspaceCarbonUsage.svelte # Workspace detail
    │   ├── CarbonBadge.svelte          # Compact badge
    │   └── index.js                    # Exports
    │
    └── src/api/carbon.js (API client)
            │
            ↓
      ada-api (proxy)
            │
            ↓
      ada-carbon-monitoring-api
```

## Using Components

### Import

```javascript
import {
  CarbonDashboard,
  CarbonIntensityForecast,
  CarbonEquivalencies,
  CarbonStackedBarChart,
  CarbonHeatmap,
  WorkspaceCarbonUsage,
  CarbonBadge
} from "$components/Carbon";
```

---

## CarbonDashboard

The main dashboard component that combines all carbon views.

```svelte
<CarbonDashboard />
```

### Features
- Summary cards (energy, carbon, workspaces, CPU time)
- Carbon intensity forecast
- Stacked bar chart (day/month/year views)
- GitHub-style heatmap
- Carbon equivalencies
- Workspace breakdown table

### Demo Mode
When running with fake data (`carbon-labs-demo` branch), displays an orange banner:
```
⚗️ Demo Mode - Displaying simulated data for demonstration purposes
```

### Data Loading
Fetches data in parallel on mount:
- `getMySummary()` - User's carbon summary
- `getMyUsage()` - User's workspace usage
- `getHeatmapData()` - Year heatmap data
- `getHistoricalData()` - Chart data for all views

---

## CarbonIntensityForecast

Line chart showing UK grid carbon intensity with best 3-hour window highlighted.

```svelte
<CarbonIntensityForecast defaultRange="working" />
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `defaultRange` | string | "working" | Initial view: "working", "24h", "48h", "custom" |

### Features
- Line chart with Chart.js
- Highlights best 3-hour low-carbon window (green background)
- "Now" marker (dashed vertical line)
- Range selector tabs
- Auto-refresh timestamp in subtitle

### Range Options
| Range | Description |
|-------|-------------|
| Working | 8:00 AM - 5:00 PM (today or tomorrow) |
| 24h | Next 24 hours |
| 48h | Next 48 hours |
| Custom | User-defined range |

### API Response Handling
Transforms API response format:
```javascript
// API returns:
{ forecasts: [{ from_time, to_time, intensity_forecast, intensity_index }] }

// Component expects:
{ periods: [{ from, to, intensity: { forecast, actual, index } }] }
```

---

## CarbonStackedBarChart

Stacked bar chart showing busy vs idle breakdown.

```svelte
<CarbonStackedBarChart
  defaultDataType="carbon"
  defaultTimeView="day"
  title="Carbon Usage"
/>
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | object | null | External data (uses API if not provided) |
| `defaultDataType` | string | "carbon" | "carbon" or "electricity" |
| `defaultTimeView` | string | "day" | "day", "month", or "year" |
| `title` | string | "" | Chart title |

### Features
- Stacked bars (busy = green, idle = gray)
- Toggle between carbon (gCO2eq) and electricity (kWh)
- Day/month/year view selector
- Date picker for specific periods
- Dynamic data fetching on view change

### Data Format
```javascript
{
  labels: ["00:00", "01:00", "02:00", ...],  // Time labels
  busy: [12.5, 15.3, 8.7, ...],              // Busy values
  idle: [3.2, 4.1, 2.8, ...]                 // Idle values
}
```

---

## CarbonHeatmap

GitHub-style year heatmap showing daily carbon footprint.

```svelte
<CarbonHeatmap
  year={2026}
  title="2026 Carbon Footprint"
/>
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | object | null | External data (uses API if not provided) |
| `year` | number | current | Year to display |
| `maxValue` | number | null | Override color scale maximum |
| `title` | string | "" | Component title |

### Features
- Full year grid (52-53 weeks × 7 days)
- Color gradient from green (low) to red (high)
- Month labels
- Day-of-week labels
- Hover tooltips with exact values
- Legend with color scale

### Data Format
```javascript
{
  year: 2026,
  days: [
    { date: "2026-01-01", value: 125.5 },
    { date: "2026-01-02", value: 143.2 },
    ...
  ],
  max: 250.0  // Maximum value for color scaling
}
```

### March 2025 Cutoff
Data before March 2025 displays as 0 (gray) due to Prometheus label changes.

---

## CarbonEquivalencies

Displays carbon in relatable real-world terms.

```svelte
<CarbonEquivalencies
  gco2eq={1500}
  equivalencies={data}
  showTotal={true}
/>
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `gco2eq` | number | 0 | Total carbon in gCO2eq |
| `equivalencies` | object | {} | Equivalencies from API |
| `showTotal` | boolean | true | Show total emissions header |

### Features
- Grid of equivalency cards with icons
- Hover effects
- Responsive layout
- Icon mapping for each equivalency type

### Equivalency Types
| Key | Icon | Description |
|-----|------|-------------|
| smartphone_charge | 📱 | Smartphone charges |
| miles_driven | 🚗 | Miles driven |
| trees_day | 🌳 | Tree-days to offset |
| streaming_hours | 📺 | HD streaming hours |
| kettle_boil | ☕ | Liters boiled |

---

## WorkspaceCarbonUsage

Per-workspace carbon tracking display.

```svelte
<WorkspaceCarbonUsage
  workspaceId="abc123"
  workspaceName="My Workspace"
  compact={false}
/>
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `workspaceId` | string | required | Workspace ID |
| `workspaceName` | string | "" | Display name |
| `compact` | boolean | false | Use compact layout |

### Features
- Real-time carbon tracking
- CPU usage breakdown
- Energy consumption
- Carbon emissions
- Equivalencies (in full mode)

---

## CarbonBadge

Compact carbon indicator for workspace cards.

```svelte
<CarbonBadge workspaceId="abc123" />
```

### Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `workspaceId` | string | required | Workspace ID |

### Features
- Small footprint badge
- Shows total gCO2eq
- Color-coded by intensity
- Loading state
- Error handling

### Usage in WorkspaceCard
```svelte
<div class="workspace-card">
  <div class="workspace-info">
    <span>{workspace.name}</span>
    <CarbonBadge workspaceId={workspace.id} />
  </div>
</div>
```

---

## API Client

The `carbon.js` API client provides all data fetching functions.

```javascript
import {
  getCurrentIntensity,
  getIntensityForecast,
  calculateCarbon,
  getEquivalencies,
  trackWorkspaces,
  getActiveWorkspaces,
  getWorkspacesSummary,
  getMySummary,
  getMyUsage,
  getHistoricalData,
  getHeatmapData,
  getWorkspaceCarbon,
  formatCarbon,
  formatEnergy,
  getIntensityColor
} from "$api/carbon";
```

### Key Functions

```javascript
// Get user's carbon summary
const summary = await getMySummary();

// Get historical data for charts
const data = await getHistoricalData({
  view: "month",
  month: "2026-01",
  data_type: "carbon"
});

// Get heatmap data
const heatmap = await getHeatmapData({ year: 2026 });

// Format values for display
formatCarbon(1500);  // "1.5 kg CO₂eq"
formatEnergy(0.5);   // "0.50 kWh"

// Get color for intensity value
getIntensityColor(185);  // "moderate" → yellow
```

---

## Styling

Components use:
- **CSS Variables** for theming
- **SMUI** (Svelte Material UI) components
- **Chart.js** for visualizations
- **Scoped styles** for component isolation

### Color Scheme
| Context | Color |
|---------|-------|
| Busy usage | Green (#4caf50) |
| Idle usage | Gray (#9e9e9e) |
| Low intensity | Green |
| Moderate intensity | Yellow |
| High intensity | Orange |
| Very high intensity | Red |

---

## Branch Structure

| Branch | Features |
|--------|----------|
| `carbon-labs-platform` | Production - Carbon in Labs sidebar |
| `carbon-labs-demo` | Demo mode with fake data banner |

---

## Reference Implementations

The `source/charts/` directory contains vanilla JS reference implementations:
- `stacked_bar_chart/` - Stacked bar chart
- `github_style/` - Heatmap
- `busy_only_bar_chart/` - Single dataset bar chart
- `busy_only_github_style/` - Busy-only heatmap

These can be used as references for porting to other frameworks.
