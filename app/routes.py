from flask import render_template, jsonify
from app import app
from app.sms import send_test_alert
from app.utils import fetch_bengaluru_weather

@app.route('/')
def index():
    weather_data = fetch_bengaluru_weather()
    return render_template('index.html', data=weather_data)

@app.route('/send-test-alert', methods=['POST'])
def send_test_alert_route():
    try:
        sid = send_test_alert()
        return jsonify({"status": "sent", "sid": sid})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500