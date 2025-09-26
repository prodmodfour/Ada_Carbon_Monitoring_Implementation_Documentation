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
    labels: Array.from({ length: 31 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      {
        label: "Idle (kWh)",
        data: [146.8611395548933, 189.69763170539906, 190.56588539310425, 186.47708497449997, 187.41748595913214, 187.16834721786913, 186.83561563352106, 188.45224998403492, 196.41502025816067, 199.57430463349306, 195.26761725951158, 192.55786521465308, 205.4925059124255, 219.40932089279875, 226.767839129668, 242.0005389891675, 285.54763937077223, 214.0793149416927, 265.7776505766305, 207.00554463361416, 178.5844964352023, 212.66487413839923, 182.11930725030317, 161.42251310176175, 218.41619578313373, 214.78316993873614, 214.05135115558824, 216.7529861010044, 222.9660282235582, 215.18118643814373, 200.16451655576859],
        backgroundColor: "rgba(54, 162, 235, 0.6)",
      },
      {
        label: "Busy (kWh)",
        data: [48.273342748137395, 77.35775679756446, 78.09040619857507, 72.15954264562257, 73.02338907066046, 80.18505140354851, 66.39964177873179, 77.1962405278634, 88.81521522004593, 79.41123969923203, 72.88642665349226, 69.32973719360842, 84.71908788679039, 80.94403653841526, 78.89646908198355, 74.23215048379885, 67.52853575909366, 63.57714147437362, 85.04879976080424, 94.51690465522503, 86.87788083415468, 97.41302824645652, 77.76990087505884, 51.601945729924864, 66.88210711535298, 62.96822476658219, 82.18852640969332, 93.13827904390607, 84.68901841313358, 73.03306909856884, 71.77506312831899],
        backgroundColor: "rgba(255, 99, 132, 0.6)",
      },
    ],
  },
  carbon: {
    labels: Array.from({ length: 31 }, (_, i) => `Day ${i + 1}`),
    datasets: [
      {
        label: "Idle (gCO2eq)",
        data: [24451.76527298199, 25791.155273794207, 14086.507328917733, 12852.720706403345, 18724.10517581379, 30028.760223867983, 33492.58110775633, 35479.376611090076, 29447.33344480824, 19209.768108225006, 16055.152367245717, 21461.97593668513, 23878.47682597182, 19142.27986825686, 23454.51207246553, 20598.63890279946, 25353.816260634216, 20802.04983086709, 35271.943366076695, 32637.796452858474, 20918.760562629017, 23112.514123004858, 21170.1762618516, 9065.247775195432, 11270.828268540594, 10619.981510089241, 19545.535213191728, 22454.660949245936, 9736.177421012386, 19463.24698962507, 17241.942392730758],
        backgroundColor: "rgba(75, 192, 192, 0.6)",
      },
      {
        label: "Busy (gCO2eq)",
        data: [7836.498330591823, 10559.304582168737, 5773.184663154071, 4972.428973639871, 7387.39171002295, 12524.993115491798, 12047.578566937047, 14533.83636732076, 13214.348009654821, 7642.07281412579, 6003.52295898933, 7778.579746453833, 9900.87674702955, 7132.445464487917, 8096.969499455665, 6022.667325744087, 6016.089297429339, 6419.9202310615165, 12484.272359157683, 14968.853600535534, 10046.928759241498, 10454.80885023819, 9056.787472494274, 2898.7125009722236, 3461.983922994953, 3130.9335676509027, 8040.446168344962, 9544.473080320084, 3683.413216637048, 6521.622231933039, 6203.943070095581],
        backgroundColor: "rgba(255, 159, 64, 0.6)",
      },
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
