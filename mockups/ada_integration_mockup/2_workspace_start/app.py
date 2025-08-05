from flask import Flask, render_template
import random

app = Flask(__name__)

@app.route('/')
def index():
    """
    Renders the main dashboard page.
    """

    carbon_usage_kwh = round(random.uniform(0.001, 0.005), 5)
    
    return render_template('index.html', carbon_usage=carbon_usage_kwh)

if __name__ == '__main__':

    app.run(port=5004,debug=True)
