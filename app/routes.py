from flask import render_template, jsonify, request
from app import app
from app.sms import send_test_alert
from app.utils import fetch_dynamic_location

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send-test-alert', methods=['POST'])
def send_test_alert_route():
    try:
        sid = send_test_alert()
        return jsonify({"status": "sent", "sid": sid})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

@app.route('/search')
def search():
    query = request.args.get('q')
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    try:
        # Prioritize exact GPS coordinates if provided
        if lat and lon:
            data = fetch_dynamic_location(lat=lat, lon=lon)
        elif query:
            data = fetch_dynamic_location(query=query)
        else:
            return jsonify({"error": "No location data provided"}), 400
            
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500