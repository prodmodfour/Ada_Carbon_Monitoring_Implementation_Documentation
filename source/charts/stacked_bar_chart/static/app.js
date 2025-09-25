// ------- State -------
let dataType = "electricity"; // 'electricity' | 'carbon'
let timeView = "day";         // 'day' | 'month' | 'year'
let selectedDate = "2025-09-24";
let selectedMonth = "2025-09";
let chartInstance = null;

// ------- Mock Data (same values as the React version) -------
const dailyData = {
  electricity: {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      { label: "Idle (kWh)", 
        data: [7.882639699167956, 7.861397710693467, 7.862701033258337, 7.8732190420193096, 
          7.87621377515129, 7.87700145327758, 7.878373860422522, 7.877308176886844, 
          7.879179778300481, 7.847982590722365, 7.816376696894171, 7.798660551220291, 
          7.888642223357256, 7.9658935880648984, 7.961157702468439, 7.955895207921866, 
          7.93222598252861, 7.925460112515643, 7.933368851423259, 7.9370395732016155, 
          7.938121500411901, 7.946116997851059, 7.9870637961261455, 7.995591801513738], backgroundColor: "rgba(54, 162, 235, 0.6)" },
      { label: "Busy (kWh)", 
        data: [3.0186476852602904, 2.9985820558931016, 2.9201715248295015, 2.7938944274530626, 
          2.7589662945204454, 2.7523992221433766, 2.7350006819684953, 2.748993405379454, 
          2.7256481955482363, 2.751880049056208, 3.2834019510026757, 3.409178432954951, 
          3.27910238159291, 3.227234120055753, 3.3575987737413855, 3.6672744938927373, 
          3.7639382820495135, 3.707136679051191, 3.709359906112237, 3.659333622732844, 
          3.646849273993562, 3.615326243978524, 3.4417615547757263, 3.3860775395782867], backgroundColor: "rgba(255, 99, 132, 0.6)" },
    ],
  },
  carbon: {
    labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
    datasets: [
      { label: "Idle (gCO2eq)", 
        data: [1087.8042784851775, 974.8133161259921, 892.416567274822, 1015.6452564204905, 
          1126.298569846634, 1252.4432310711304, 1303.8708738999278, 1224.9214215059096, 
          1103.0851689620608, 988.8458064310148, 875.4341900521491, 686.2821285073851, 
          611.3697723101891, 617.3567530750353, 636.8926161974742, 811.5013112080251, 
          1074.8166206326218, 1303.738188508824, 1439.9064465333256, 1527.8801178413175, 
          1516.1812065786764, 1446.1932936088967, 1206.0466332150472, 1067.4115055020814], backgroundColor: "rgba(75, 192, 192, 0.6)" },
      { label: "Busy (gCO2eq)", 
        data: [416.5733805659048, 371.82417493071483, 331.439468068142, 360.41238114135666, 
          394.53218011639166, 437.63147632081206, 452.6426128657399, 427.4684745365027, 
          381.59074737671256, 346.7368861811205, 367.7410185123436, 300.007702100073, 
          254.13043457348377, 250.11064430435292, 268.6079018993034, 374.0619983770999, 
          510.0136372177215, 609.8239837038744, 673.2488229594038, 704.4217223760313, 
          696.5482113327545, 657.989376404094, 519.7059947711158, 452.0413515336881], backgroundColor: "rgba(255, 159, 64, 0.6)" },
    ],
  },
};

const monthlyData = {
  electricity: {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      { label: "Idle (kWh)", data: Array.from({ length: 30 }, () => Math.random() * 5 + 5), backgroundColor: "rgba(54, 162, 235, 0.6)" },
      { label: "Busy (kWh)", data: Array.from({ length: 30 }, () => Math.random() * 15 + 10), backgroundColor: "rgba(255, 99, 132, 0.6)" },
    ],
  },
  carbon: {
    labels: Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      { label: "Idle (gCO2eq)", data: Array.from({ length: 30 }, () => Math.random() * 1000 + 1000), backgroundColor: "rgba(75, 192, 192, 0.6)" },
      { label: "Busy (gCO2eq)", data: Array.from({ length: 30 }, () => Math.random() * 3000 + 2000), backgroundColor: "rgba(255, 159, 64, 0.6)" },
    ],
  },
};

const yearlyData = {
  electricity: {
    labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    datasets: [
      { label: "Idle (kWh)", data: [150,160,170,180,200,220,230,220,200,180,160,150], backgroundColor: "rgba(54, 162, 235, 0.6)" },
      { label: "Busy (kWh)", data: [400,420,450,480,550,600,620,610,550,480,430,400], backgroundColor: "rgba(255, 99, 132, 0.6)" },
    ],
  },
  carbon: {
    labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    datasets: [
      { label: "Idle (gCO2eq)", data: [30000,32000,34000,36000,40000,44000,46000,44000,40000,36000,32000,30000], backgroundColor: "rgba(75, 192, 192, 0.6)" },
      { label: "Busy (gCO2eq)", data: [80000,84000,90000,96000,110000,120000,124000,122000,110000,96000,86000,80000], backgroundColor: "rgba(255, 159, 64, 0.6)" },
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
  return `${cap(dataType)} Usage - ${cap(timeView)} View${titleDate}`;
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
      },
      scales: {
        x: { stacked: true },
        y: {
          stacked: true,
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
    // Update y-axis title and title text via full re-render (keeps parity with React impl)
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
