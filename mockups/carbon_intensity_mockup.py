from flask import Flask, render_template_string
from prometheus_client import make_wsgi_app, Gauge
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import requests
import time
import threading


CARBON_INTENSITY = Gauge('carbon_intensity_gco2_per_kwh', 'Carbon intensity of electricity in gCO2/kWh')
CARBON_INTENSITY_INDEX = Gauge('carbon_intensity_index', 'Carbon intensity index (e.g., very low, low, moderate, high, very high)')

GENERATION_BIOMASS = Gauge('generation_biomass_percent', 'Percentage of electricity generated from biomass')
GENERATION_COAL = Gauge('generation_coal_percent', 'Percentage of electricity generated from coal')
GENERATION_GAS = Gauge('generation_gas_percent', 'Percentage of electricity generated from gas')
GENERATION_HYDRO = Gauge('generation_hydro_percent', 'Percentage of electricity generated from hydro')
GENERATION_IMPORTS = Gauge('generation_imports_percent', 'Percentage of electricity imported')
GENERATION_NUCLEAR = Gauge('generation_nuclear_percent', 'Percentage of electricity generated from nuclear')
GENERATION_OTHER = Gauge('generation_other_percent', 'Percentage of electricity generated from other sources')
GENERATION_SOLAR = Gauge('generation_solar_percent', 'Percentage of electricity generated from solar')
GENERATION_WIND = Gauge('generation_wind_percent', 'Percentage of electricity generated from wind')

def fetch_carbon_intensity_data():
    while True:
        try:
            intensity_response = requests.get('https://api.carbonintensity.org.uk/intensity')
            intensity_response.raise_for_status()  # Raise an exception for bad status codes
            intensity_data = intensity_response.json()['data'][0]['intensity']

            CARBON_INTENSITY.set(intensity_data['actual'])
            
            index_mapping = {
                "very low": 1,
                "low": 2,
                "moderate": 3,
                "high": 4,
                "very high": 5
            }
            CARBON_INTENSITY_INDEX.set(index_mapping.get(intensity_data['index'], 0))

            generation_response = requests.get('https://api.carbonintensity.org.uk/generation')
            generation_response.raise_for_status()
            generation_mix = generation_response.json()['data']['generationmix']

            for gen_type in generation_mix:
                fuel = gen_type['fuel']
                perc = gen_type['perc']
                if fuel == 'biomass':
                    GENERATION_BIOMASS.set(perc)
                elif fuel == 'coal':
                    GENERATION_COAL.set(perc)
                elif fuel == 'gas':
                    GENERATION_GAS.set(perc)
                elif fuel == 'hydro':
                    GENERATION_HYDRO.set(perc)
                elif fuel == 'imports':
                    GENERATION_IMPORTS.set(perc)
                elif fuel == 'nuclear':
                    GENERATION_NUCLEAR.set(perc)
                elif fuel == 'other':
                    GENERATION_OTHER.set(perc)
                elif fuel == 'solar':
                    GENERATION_SOLAR.set(perc)
                elif fuel == 'wind':
                    GENERATION_WIND.set(perc)

            print("Successfully updated carbon intensity and generation mix data.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Carbon Intensity API: {e}")
        
        time.sleep(900)

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UK Carbon Intensity</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        .card {
            background-color: #ffffff;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        .intensity-card {
            border-left: 5px solid;
        }
        .very-low { border-color: #22c55e; }
        .low { border-color: #84cc16; }
        .moderate { border-color: #facc15; }
        .high { border-color: #f97316; }
        .very-high { border-color: #ef4444; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="container mx-auto p-4 md:p-8 max-w-4xl">
        <h1 class="text-3xl font-bold mb-6 text-center">UK Carbon Intensity</h1>
        
        <div id="data-container">
            <!-- Data will be loaded here -->
            <div class="text-center">
                <p class="text-lg">Loading data...</p>
            </div>
        </div>

        <div class="mt-8 text-center text-sm text-gray-500">
            <p>Data from the <a href="https://carbonintensity.org.uk/" target="_blank" class="text-blue-500 hover:underline">National Grid ESO</a>. Refreshes automatically.</p>
            <p>Metrics are exposed for Prometheus at <a href="/metrics" class="text-blue-500 hover:underline">/metrics</a>.</p>
        </div>
    </div>

    <script>
        function getIntensityColor(index) {
            const colors = {
                "very low": "very-low",
                "low": "low",
                "moderate": "moderate",
                "high": "high",
                "very high": "very-high"
            };
            return colors[index] || "bg-gray-200";
        }

        function getFuelColor(fuel) {
            const colors = {
                "biomass": "bg-green-600",
                "coal": "bg-gray-800",
                "gas": "bg-orange-500",
                "hydro": "bg-blue-500",
                "imports": "bg-purple-500",
                "nuclear": "bg-yellow-400",
                "other": "bg-gray-400",
                "solar": "bg-yellow-300",
                "wind": "bg-cyan-400"
            };
            return colors[fuel] || "bg-gray-200";
        }

        async function fetchData() {
            try {
                const intensityRes = await fetch('https://api.carbonintensity.org.uk/intensity');
                const generationRes = await fetch('https://api.carbonintensity.org.uk/generation');
                
                const intensityData = await intensityRes.json();
                const generationData = await generationRes.json();

                const intensity = intensityData.data[0].intensity;
                const generationMix = generationData.data.generationmix;

                const container = document.getElementById('data-container');
                container.innerHTML = `
                    <div class="card intensity-card ${getIntensityColor(intensity.index)}">
                        <h2 class="text-xl font-semibold mb-2">Current Carbon Intensity</h2>
                        <p class="text-5xl font-bold">${intensity.actual} <span class="text-2xl font-normal">gCO₂/kWh</span></p>
                        <p class="text-xl capitalize mt-2">${intensity.index}</p>
                        <p class="text-sm text-gray-500 mt-1">From: ${new Date(intensityData.data[0].from).toLocaleString()} - To: ${new Date(intensityData.data[0].to).toLocaleString()}</p>
                    </div>

                    <div class="card">
                        <h2 class="text-xl font-semibold mb-4">Generation Mix</h2>
                        <div class="space-y-3">
                            ${generationMix.map(fuel => `
                                <div class="w-full">
                                    <div class="flex justify-between mb-1">
                                        <span class="text-base font-medium text-gray-700 capitalize">${fuel.fuel}</span>
                                        <span class="text-sm font-medium text-gray-700">${fuel.perc}%</span>
                                    </div>
                                    <div class="w-full bg-gray-200 rounded-full h-4">
                                        <div class="${getFuelColor(fuel.fuel)} h-4 rounded-full" style="width: ${fuel.perc}%"></div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;

            } catch (error) {
                console.error("Failed to fetch data:", error);
                const container = document.getElementById('data-container');
                container.innerHTML = '<div class="card text-center text-red-500"><p>Could not load data. Please try again later.</p></div>';
            }
        }

        fetchData();
        setInterval(fetchData, 300000); // 300000 ms = 5 minutes
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

if __name__ == '__main__':
    data_fetch_thread = threading.Thread(target=fetch_carbon_intensity_data, daemon=True)
    data_fetch_thread.start()

    app.run(host='0.0.0.0', port=8000)
