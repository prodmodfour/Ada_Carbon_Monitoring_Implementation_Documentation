from flask import Flask, render_template, jsonify, request
from datetime import date, timedelta
import random

app = Flask(__name__)

@app.route("/")
def index():
    # Default to current year; you can change this
    return render_template("index.html", default_year=date.today().year)

@app.route("/data")
def data():
    """
    Returns mock daily carbon usage for the requested year:
    { year: 2025, days: [{date: "2025-01-01", value: 1234.5}, ...], max: <maxValue> }
    """
    year = int(request.args.get("year", date.today().year))

    # Make mock data reproducible per year
    rng = random.Random(year)

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    n_days = (end - start).days + 1

    days = []
    max_val = 0.0

    for i in range(n_days):
        d = start + timedelta(days=i)
        # Seasonal-ish fake pattern + noise (gCO2eq)
        # Winter higher, summer lower, with weekday/weekend variation
        month = d.month
        base = {
            12: 120000, 1: 120000, 2: 110000,
            3: 90000, 4: 85000, 5: 80000,
            6: 75000, 7: 75000, 8: 78000,
            9: 85000, 10: 95000, 11: 105000
        }[month]
        weekday_boost = 1.0 if d.weekday() >= 5 else 1.15  # weekdays a bit higher
        noise = rng.uniform(-0.08, 0.08)  # ±8%
        val = base * weekday_boost * (1.0 + noise)

        # Add a few "spike" days
        if rng.random() < 0.03:
            val *= rng.uniform(1.3, 1.8)

        max_val = max(max_val, val)
        days.append({"date": d.isoformat(), "value": round(val, 2)})

    return jsonify({"year": year, "days": days, "max": round(max_val, 2)})

if __name__ == "__main__":
    app.run(debug=True)
