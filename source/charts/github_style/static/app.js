// --- Config (larger cells) ---
const CELL = 18;          // size of a day square (px)
const GAP = 4;            // gap between squares (px)
const PADDING_TOP = 24;   // top padding to fit month labels (px)
const PADDING_LEFT = 36;  // left padding to fit weekday labels if needed
const ROWS = 7;           // Sun..Sat

// Color scale: green -> orange -> red
function colorFor(value, max) {
  if (value <= 0 || !isFinite(max) || max <= 0) return "#e5e7eb"; // light gray for 0/invalid
  const r = value / max; // 0..1
  if (r <= 0.5) {
    return lerpColor("#22c55e", "#f59e0b", r / 0.5);
  } else {
    return lerpColor("#f59e0b", "#ef4444", (r - 0.5) / 0.5);
  }
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

// Compute the Sunday on or before Jan 1 so weeks align like GitHub
function startOfCalendar(year) {
  const first = new Date(year, 0, 1); // Jan 1
  const day = first.getDay(); // 0 Sun..6 Sat
  return new Date(year, 0, 1 - day);
}

function endOfCalendar(year) {
  const last = new Date(year, 11, 31); // Dec 31
  const day = last.getDay();
  // Move to Saturday of the last week
  return new Date(year, 11, 31 + (6 - day));
}

async function fetchYear(year) {
  const res = await fetch(`/data?year=${year}`);
  if (!res.ok) throw new Error("Failed to fetch data");
  return await res.json();
}

function fmtNumber(n) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function formatDateISO(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function monthNames() {
  return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
}

// Render the heatmap SVG
function renderHeatmap(data) {
  const svg = document.getElementById("heatmap");
  const tooltip = document.getElementById("tooltip");
  const year = data.year;
  const max = data.max;
  const values = new Map(data.days.map(d => [d.date, d.value]));

  const calStart = startOfCalendar(year);
  const calEnd = endOfCalendar(year);

  // Number of weeks (columns)
  const nDays = Math.round((calEnd - calStart) / (1000 * 60 * 60 * 24)) + 1;
  const weeks = Math.ceil(nDays / 7);

  // Compute intrinsic size
  const width = PADDING_LEFT + weeks * (CELL + GAP) - GAP + 8;
  const height = PADDING_TOP + ROWS * (CELL + GAP) - GAP + 8;

  // Make the SVG responsive: scale to container width (no inner scrollbars)
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  svg.innerHTML = "";

  // Month labels (simple row; not strictly aligned to columns, but responsive)
  const monthLabels = document.getElementById("month-labels");
  monthLabels.innerHTML = "";
  for (let m = 0; m < 12; m++) {
    const label = document.createElement("div");
    label.textContent = monthNames()[m];
    label.className = "px-1";
    monthLabels.appendChild(label);
  }

  // Draw cells
  let d = new Date(calStart);
  for (let col = 0; col < weeks; col++) {
    for (let row = 0; row < ROWS; row++) {
      const x = PADDING_LEFT + col * (CELL + GAP);
      const y = PADDING_TOP + row * (CELL + GAP);

      const iso = formatDateISO(d);
      const inYear = d.getFullYear() === year;
      const value = values.get(iso) || 0;
      const fill = inYear ? colorFor(value, max) : "#f3f4f6";

      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", CELL);
      rect.setAttribute("height", CELL);
      rect.setAttribute("rx", 3);
      rect.setAttribute("ry", 3);
      rect.setAttribute("fill", fill);
      rect.setAttribute("data-date", iso);
      rect.setAttribute("data-value", value);

      if (inYear) {
        rect.style.cursor = "pointer";
        rect.addEventListener("mouseenter", (e) => {
          const rectBox = e.target.getBoundingClientRect();
          tooltip.innerHTML = `
            <div class="font-medium text-gray-800">${iso}</div>
            <div class="text-gray-600">${fmtNumber(value)} gCO₂e</div>
          `;
          tooltip.style.left = `${rectBox.left + rectBox.width / 2}px`;
          tooltip.style.top = `${rectBox.top - 8 + window.scrollY}px`;
          tooltip.style.transform = "translate(-50%, -100%)";
          tooltip.style.display = "block";
        });
        rect.addEventListener("mouseleave", () => {
          tooltip.style.display = "none";
        });
        rect.addEventListener("focusout", () => {
          tooltip.style.display = "none";
        });
      }

      svg.appendChild(rect);
      d.setDate(d.getDate() + 1);
      if (d > calEnd) break;
    }
  }
}

// Wire up UI
async function boot() {
  const yearInput = document.getElementById("year");
  const reloadBtn = document.getElementById("reload");

  async function loadYear() {
    reloadBtn.disabled = true;
    reloadBtn.textContent = "Loading…";
    try {
      const year = parseInt(yearInput.value, 10);
      const data = await fetchYear(year);
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
