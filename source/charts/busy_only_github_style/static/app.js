// --- Layout config ---
const CELL = 18;
const GAP = 4;
const PADDING_TOP = 28;     // room for month labels inside the SVG
const PADDING_LEFT = 36;    // room for weekday labels if you add them later
const ROWS = 7;             // Sun..Sat
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

// Color scale: green -> orange -> red
function colorFor(value, max) {
  if (value <= 0 || !isFinite(max) || max <= 0) return "#e5e7eb";
  const r = Math.max(0, Math.min(1, value / max));
  return (r <= 0.5)
    ? lerpColor("#22c55e", "#f59e0b", r / 0.5)
    : lerpColor("#f59e0b", "#ef4444", (r - 0.5) / 0.5);
}
function lerpColor(a, b, t) {
  const ca = hexToRgb(a), cb = hexToRgb(b);
  const r = Math.round(ca.r + (cb.r - ca.r) * t);
  const g = Math.round(ca.g + (cb.g - ca.g) * t);
  const b2 = Math.round(ca.b + (cb.b - ca.b) * t);
  return `rgb(${r}, ${g}, ${b2})`;
}
function hexToRgb(hex) {
  const n = hex.replace("#", "");
  const bigint = parseInt(n, 16);
  return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
}

// Calendar helpers
function startOfCalendar(year) {
  const first = new Date(year, 0, 1);
  return new Date(year, 0, 1 - first.getDay()); // previous Sunday
}
function endOfCalendar(year) {
  const last = new Date(year, 11, 31);
  return new Date(year, 11, 31 + (6 - last.getDay())); // next Saturday
}
function daysBetween(a, b) {
  return Math.round((b - a) / 86400000);
}
async function fetchYear(year) {
  const res = await fetch(`/data?year=${year}`);
  if (!res.ok) throw new Error("Failed to fetch data");
  return await res.json();
}
function fmtNumber(n) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}
function iso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

// --- NEW: allow dict-of-arrays input & custom max redness ---
const MONTH_NAME_TO_INDEX = {
  "january": 0, "jan": 0, 1: 0,
  "february": 1, "feb": 1, 2: 1,
  "march": 2, "mar": 2, 3: 2,
  "april": 3, "apr": 3, 4: 3,
  "may": 4, 5: 4,
  "june": 5, "jun": 5, 6: 5,
  "july": 6, "jul": 6, 7: 6,
  "august": 7, "aug": 7, 8: 7,
  "september": 8, "sep": 8, 9: 8,
  "october": 9, "oct": 9, 10: 9,
  "november": 10, "nov": 10, 11: 10,
  "december": 11, "dec": 11, 12: 11,
};
function getMonthIndex(key) {
  const k = (typeof key === "string") ? key.toLowerCase().trim() : key;
  return MONTH_NAME_TO_INDEX.hasOwnProperty(k) ? MONTH_NAME_TO_INDEX[k] : null;
}
function daysInMonth(year, monthIndex) {
  return new Date(year, monthIndex + 1, 0).getDate();
}
/**
 * Build the standard data payload from a dict-of-arrays:
 * - dict keys can be "January".."December", "Jan".."Dec", or 1..12
 * - each array is per-day values; missing entries default to 0
 * - maxRedness overrides the scale's max; if falsy, auto uses data max
 */
function buildDataFromDict(dict, year, maxRedness) {
  const days = [];
  let computedMax = 0;

  for (let m = 0; m < 12; m++) {
    const monthName = Object.keys(dict).find(k => getMonthIndex(k) === m);
    const arr = monthName ? dict[monthName] : [];
    const nDays = daysInMonth(year, m);
    for (let d = 1; d <= nDays; d++) {
      const v = Number(arr?.[d - 1] ?? 0) || 0;
      const date = new Date(year, m, d);
      const vClamped = isFinite(v) ? Math.max(0, v) : 0;
      days.push({ date: iso(date), value: vClamped });
      if (vClamped > computedMax) computedMax = vClamped;
    }
  }
  const effectiveMax = (maxRedness ?? maxRedness === 0) && isFinite(maxRedness)
    ? Number(maxRedness)
    : computedMax;

  return {
    year,
    days,
    max: computedMax,            // actual data max (for reference)
    maxRedness: effectiveMax     // what the color scale will use
  };
}

// --- Render ---
function renderHeatmap(data) {
  const svg = document.getElementById("heatmap");
  const tooltip = document.getElementById("tooltip");
  const year = data.year;

  // If present, use caller’s scale override; else fall back to data.max
  const scaleTop = isFinite(data.maxRedness) ? data.maxRedness : data.max;

  const values = new Map(data.days.map(d => [d.date, d.value]));
  const calStart = startOfCalendar(year);
  const calEnd = endOfCalendar(year);

  const nDays = daysBetween(calStart, calEnd) + 1;
  const weeks = Math.ceil(nDays / 7);

  const width = PADDING_LEFT + weeks * (CELL + GAP) - GAP + 8;
  const height = PADDING_TOP + ROWS * (CELL + GAP) - GAP + 8;

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";

  // Month labels
  const gMonths = document.createElementNS("http://www.w3.org/2000/svg", "g");
  gMonths.setAttribute("font-size", "12");
  gMonths.setAttribute("fill", "#6b7280");
  gMonths.setAttribute("font-family", "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica Neue, Arial, Apple Color Emoji, Segoe UI Emoji");
  for (let m = 0; m < 12; m++) {
    const firstOfMonth = new Date(year, m, 1);
    const diffDays = Math.max(0, daysBetween(calStart, firstOfMonth));
    const col = Math.floor(diffDays / 7);
    const x = PADDING_LEFT + col * (CELL + GAP);
    const y = 14;
    const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", x);
    t.setAttribute("y", y);
    t.textContent = MONTHS[m];
    gMonths.appendChild(t);
  }
  svg.appendChild(gMonths);

  // Cells
  let d = new Date(calStart);
  for (let col = 0; col < weeks; col++) {
    for (let row = 0; row < ROWS; row++) {
      const x = PADDING_LEFT + col * (CELL + GAP);
      const y = PADDING_TOP + row * (CELL + GAP);

      const dateIso = iso(d);
      const inYear = d.getFullYear() === year;
      const value = values.get(dateIso) || 0;
      const fill = inYear ? colorFor(value, scaleTop) : "#f3f4f6";

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", CELL);
      rect.setAttribute("height", CELL);
      rect.setAttribute("rx", 3);
      rect.setAttribute("ry", 3);
      rect.setAttribute("fill", fill);
      rect.setAttribute("data-date", dateIso);
      rect.setAttribute("data-value", value);

      if (inYear) {
        rect.style.cursor = "pointer";
        rect.addEventListener("mouseenter", (e) => {
          const r = e.target.getBoundingClientRect();
          tooltip.innerHTML = `
            <div class="font-medium text-gray-800">${dateIso}</div>
            <div class="text-gray-600">${fmtNumber(value)} gCO₂e</div>
          `;
          tooltip.style.left = `${r.left + r.width / 2}px`;
          tooltip.style.top = `${r.top - 8 + window.scrollY}px`;
          tooltip.style.transform = "translate(-50%, -100%)";
          tooltip.style.display = "block";
        });
        rect.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
        rect.addEventListener("focusout", () => { tooltip.style.display = "none"; });
      }

      svg.appendChild(rect);

      d.setDate(d.getDate() + 1);
      if (d > calEnd) break;
    }
  }
}

// --- UI wiring ---
async function boot() {
  const yearInput = document.getElementById("year");
  const reloadBtn = document.getElementById("reload");

  async function loadYear() {
    reloadBtn.disabled = true;
    reloadBtn.textContent = "Loading…";
    try {
      const year = parseInt(yearInput.value, 10);

      // If CUSTOM_DATA is provided, use it; otherwise fall back to server /data
      let data;
      if (window.CUSTOM_DATA && typeof window.CUSTOM_DATA === "object" && Object.keys(window.CUSTOM_DATA).length > 0) {
        data = buildDataFromDict(window.CUSTOM_DATA, year, window.MAX_REDNESS);
      } else {
        const fetched = await fetchYear(year);
        // Respect optional MAX_REDNESS even for server data
        data = {
          ...fetched,
          maxRedness: (window.MAX_REDNESS ?? window.MAX_REDNESS === 0) ? Number(window.MAX_REDNESS) : fetched.max
        };
      }

      renderHeatmap(data);
    } catch (err) {
      alert(err.message || "Failed to load data");
    } finally {
      reloadBtn.disabled = false;
      reloadBtn.textContent = "Load";
    }
  }

  reloadBtn.addEventListener("click", loadYear);
  await loadYear();
}

window.addEventListener("DOMContentLoaded", boot);
