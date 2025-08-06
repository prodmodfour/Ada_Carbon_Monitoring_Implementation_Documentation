from flask import Flask, jsonify, render_template
import threading
import sqlite3
from data_logger import start_logging
from database import DATABASE_NAME

app = Flask(__name__)


@app.route("/")
def index():
    """Redirects to the main dashboard page."""
    return render_template('dashboard.html')

@app.route("/api/v1/all_readings")
def get_all_readings():
    """API endpoint to get all historical readings from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM readings ORDER BY timestamp ASC") 
    all_readings = cursor.fetchall()
    conn.close()
    

    return jsonify([dict(row) for row in all_readings])



if __name__ == "__main__":
    logging_thread = threading.Thread(target=start_logging, daemon=True)
    logging_thread.start()
    app.run(debug=False, port=5001)