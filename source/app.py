from flask import Flask, jsonify, render_template
import threading
import sqlite3
import requests 
from data_logger import start_logging
from database import DATABASE_NAME

app = Flask(__name__)

@app.route("/")
def index():
    """Renders the main dashboard page."""
    return render_template('dashboard.html')

@app.route("/api/v1/all_readings")
def get_all_readings():
    """API endpoint to get all historical readings."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM readings ORDER BY timestamp ASC")
    all_readings = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in all_readings])

@app.route("/api/v1/carbon_intensity_forecast")
def get_carbon_forecast():
    """API endpoint to get the 48-hour carbon intensity forecast."""
    try:
        response = requests.get("https://api.carbonintensity.org.uk/intensity/fw48h")
        response.raise_for_status()
        return jsonify(response.json()['data'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/performance_summary")
def get_performance_summary():
    """Calculates and returns a summary of recent performance."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT AVG(gco2eq) FROM readings WHERE timestamp > datetime('now', '-7 days')")
    last_7_days_avg = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT AVG(gco2eq) FROM readings WHERE timestamp BETWEEN datetime('now', '-14 days') AND datetime('now', '-7 days')")
    previous_7_days_avg = cursor.fetchone()[0] or 0
    
    conn.close()
    
    improvement = 0
    if previous_7_days_avg > 0:
        improvement = ((previous_7_days_avg - last_7_days_avg) / previous_7_days_avg) * 100

    return jsonify({
        "last_7_days_avg": last_7_days_avg,
        "previous_7_days_avg": previous_7_days_avg,
        "improvement_percent": improvement
    })


# --- Main Application ---

if __name__ == "__main__":
    logging_thread = threading.Thread(target=start_logging, daemon=True)
    logging_thread.start()
    app.run(debug=False, port=5001)