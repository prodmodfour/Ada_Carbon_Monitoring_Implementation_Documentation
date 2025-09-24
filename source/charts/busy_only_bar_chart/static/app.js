// ------- State -------
let dataType = "electricity"; // 'electricity' | 'carbon'
let timeView = "day";         // 'day' | 'month' | 'year'
let selectedDate = "2025-09-24";
let selectedMonth = "2025-09";
let chartInstance = null;

// ------- Mock Data (Busy only) -------
const dailyData = {
  electricity: {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      {
        label: "Busy (kWh)",
        data: [3.3556003948636914, 3.2676301256329214, 3.2485775997099564, 3.2522741572298832, 3.202716184409748, 3.2059869138973807, 3.1768431122516367, 3.0110228622811777, 3.0668163956028716, 3.330852320176943, 3.593809328785409, 3.3409221088221552, 3.4131788491028847, 3.420672989246755, 3.6719800771770834, 3.316194212350672, 3.294501183536836, 3.1454438219340166, 3.1450082675566753, 3.0657325501699653, 3.1376824777258205, 3.0950893546618135, 3.3745630287461386, 2.6508169384646996],
        backgroundColor: "rgba(255, 99, 132, 0.6)"
      },
    ],
  },
  carbon: {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      {
        label: "Busy (gCO2eq)",
        data: [775.143691213581, 749.9211138326643, 747.1728479332729, 739.8923707698445, 733.4220062297835, 758.2159051367283, 778.3265625016209, 712.1069069295115, 685.4334644172664, 676.1630209959833, 614.5413952222591, 497.79739421441894, 476.13844944988455, 477.1838819999511, 521.4211709591527, 530.591073976046, 622.6607236884836, 600.7797699894343, 616.4216204411096, 576.3577194319096, 534.9748624522854, 405.4567054607066, 330.7071768171141, 172.30310100023104],
        backgroundColor: "rgba(255, 159, 64, 0.6)"
      },
    ],
  },
};

const monthlyData = {
  electricity: {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      {
        label: "Busy (kWh)",
        data: Array.from({ length: 30 }, () => Math.random() * 15 + 10),
        backgroundColor: "rgba(255, 99, 132, 0.6)"
      },
    ],
  },
  carbon: {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      {
        label: "Busy (gCO2eq)",
        data: Array.from({ length: 30 }, () => Math.random() * 3000 + 2000),
        backgroundColor: "rgba(255, 159, 64, 0.6)"
      },
    ],
  },
};

const yearlyData = {
  electricity: {
    labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    datasets: [
      {
        label: "Busy (kWh)",
        data: [400,420,450,480,550,600,620,610,550,480,430,400],
        backgroundColor: "rgba(255, 99, 132, 0.6)"
      },
    ],
  },
  carbon: {
    labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    datasets: [
      {
        label: "Busy (gCO2eq)",
        data: [80000,84000,90000,96000,110000,120000,124000,122000,110000,96000,86000,80000],
        backgroundColor: "rgba(255, 159, 64, 0.6)"
      },
    ],
  },
};

// ------- Helpers -------
function setActiveTab(containerEl, selectedValue) {
  const buttons = containerEl.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    const isSelected = btn.dataset.value === selectedValue;
    btn.classList.toggle("bg-white", isSelected);
    btn.classList.toggle("shadow-md", isSelected);
    btn.classList.toggle("text-blue-600", isSelected);
    btn.classList.toggle("font-semibold", isSelected);
    btn.classList.toggle("text-gray-600", !isSelected);
    btn.classList.toggle("hover:bg-gray-300", !isSelected);
  });
}

function updatePickersVisibility() {
  const dayLabel = document.querySelector('label[for="day-select"]');
  const dayInput = document.getElementById("day-select");
  const monthLabel = document.querySelector('label[for="month-select"]');
  const monthInput = document.getElementById("month-select");
  const yearLabel = document.getElementById("year-label");
  const yearValue = document.getElementById("year-value");

  if (timeView === "day") {
    dayLabel.classList.remove("hidden");
    dayInput.classList.remove("hidden");
    monthLabel.classList.add("hidden");
    monthInput.classList.add("hidden");
    yearLabel.classList.add("hidden");
    yearValue.classList.add("hidden");
  } else if (timeView === "month") {
    dayLabel.classList.add("hidden");
    dayInput.classList.add("hidden");
    monthLabel.classList.remove("hidden");
    monthInput.classList.remove("hidden");
    yearLabel.classList.add("hidden");
    yearValue.classList.add("hidden");
  } else {
    dayLabel.classList.add("hidden");
    dayInput.classList.add("hidden");
    monthLabel.classList.add("hidden");
    monthInput.classList.add("hidden");
    yearLabel.classList.remove("hidden");
    yearValue.classList.remove("hidden");
  }
}

function buildTitle() {
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  let titleDate = "";
  if (timeView === "day") {
    titleDate = ` for ${selectedDate}`;
  } else if (timeView === "month") {
    // Use day 02 to avoid TZ issues
    const date = new Date(`${selectedMonth}-02`);
    const monthName = date.toLocaleString("default", { month: "long" });
    const year = date.getFullYear();
    titleDate = ` for ${monthName} ${year}`;
  } else {
    titleDate = " for 2025";
  }
  // Clarify that we're showing Busy only
  return `${cap(dataType)} Usage (Busy Only) - ${cap(timeView)} View${titleDate}`;
}

function getDataForView() {
  if (timeView === "day") return dailyData[dataType];
  if (timeView === "month") return monthlyData[dataType];
  return yearlyData[dataType];
}

function getYAxisTitle() {
  return dataType === "electricity" ? "Usage (kWh)" : "Usage (gCO2eq)";
}

// ------- Chart Rendering -------
function renderChart() {
  const ctx = document.getElementById("chartCanvas").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  chartInstance = new Chart(ctx, {
    type: "bar",
    data: getDataForView(),
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: buildTitle(),
          font: { size: 20 },
          padding: { top: 10, bottom: 30 },
        },
        tooltip: { mode: "index", intersect: false },
        legend: { display: true },
      },
      scales: {
        x: { stacked: false },
        y: {
          stacked: false,
          beginAtZero: true,
          title: { display: true, text: getYAxisTitle() },
        },
      },
    },
  });
}

// ------- Wire up UI -------
window.addEventListener("DOMContentLoaded", () => {
  // Defaults
  document.getElementById("day-select").value = selectedDate;
  document.getElementById("month-select").value = selectedMonth;

  // Tabs
  const dataTypeTabs = document.getElementById("dataTypeTabs");
  const timeViewTabs = document.getElementById("timeViewTabs");

  setActiveTab(dataTypeTabs, dataType);
  setActiveTab(timeViewTabs, timeView);
  updatePickersVisibility();

  dataTypeTabs.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    dataType = btn.dataset.value;
    setActiveTab(dataTypeTabs, dataType);
    renderChart();
  });

  timeViewTabs.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;
    timeView = btn.dataset.value;
    setActiveTab(timeViewTabs, timeView);
    updatePickersVisibility();
    renderChart();
  });

  // Inputs
  document.getElementById("day-select").addEventListener("change", (e) => {
    selectedDate = e.target.value;
    renderChart();
  });

  document.getElementById("month-select").addEventListener("change", (e) => {
    selectedMonth = e.target.value;
    renderChart();
  });

  // Initial chart
  renderChart();
});
