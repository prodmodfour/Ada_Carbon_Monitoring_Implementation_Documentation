from flask import Flask, render_template


app = Flask(__name__)


instruments = [
    {
        "name": "ARTEMIS",
        "carbon_usage": 155
    },
    {
        "name": "EPAC",
        "carbon_usage": 210
    },
    {
        "name": "GEMINI",
        "carbon_usage": 350
    },
    {
        "name": "OCTOPUS",
        "carbon_usage": 275
    },
    {
        "name": "ULTRA",
        "carbon_usage": 180
    },
    {
        "name": "VULCAN",
        "carbon_usage": 420
    }
]

@app.route('/')
def index():
    """Renders the main instrument selection page."""
    return render_template('index.html', instruments=instruments)

if __name__ == '__main__':
    app.run(port=5005,debug=True)