from flask import Flask, jsonify
import threading
import sqlite3
from data_logger import start_logging 
from database import DATABASE_NAME 

app = Flask(__name__)

@app.route("/")
def index():
    """A simple route to confirm the server is running."""
    return "<h1>Sustainability Dashboard Backend</h1><p>The server is running and the data logger is active in the background.</p>"

@app.route("/api/v1/latest_reading")
def get_latest_reading():
    """An API endpoint to get the most recent reading from the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1")
    latest = cursor.fetchone()
    
    conn.close()
    
    if latest:
        return jsonify(dict(latest))
    else:
        return jsonify({"error": "No data available yet."}), 404


if __name__ == "__main__":

    logging_thread = threading.Thread(target=start_logging, daemon=True)
    logging_thread.start()
    
    app.run(debug=False, port=5001) 