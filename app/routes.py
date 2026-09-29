from flask import render_template, jsonify, request
from app import app
from app.sms import send_test_alert
from app.utils import fetch_dynamic_location

# Mock database of governments that have officially connected to our API
registered_webhooks = {}

# Mock database of authorized API keys issued to municipalities by MoES
AUTHORIZED_API_KEYS = {
    "moes_key_delhi_2026": "Delhi",
    "moes_key_karna_2026": "Karnataka",
    "moes_key_maha_2026": "Maharashtra"
}

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

@app.route('/api/v1/subscribe', methods=['POST'])
def subscribe_to_alerts():
    """
    Endpoint for municipalities to register their systems to receive push alerts.
    Requires a valid Bearer token in the Authorization header.
    Expects a JSON payload: {"region": "Delhi", "webhook_url": "https://their-server.com/alerts"}
    """
    # 1. SECURITY CHECK: To verify the Authorization Header
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({
            "status": "error", 
            "message": "Missing or invalid Authorization header. Expected 'Bearer <token>'"
        }), 401 # 401 Unauthorized
        
    # Extract the token string (removes the word "Bearer ")
    token = auth_header.split(" ")[1]
    
    # 2. SECURITY CHECK: To verify the key exists in our database
    if token not in AUTHORIZED_API_KEYS:
        return jsonify({
            "status": "error", 
            "message": "Invalid API Key. Access Denied."
        }), 403
        
    # 3. Process the payload
    data = request.get_json()
    if not data or 'region' not in data or 'webhook_url' not in data:
        return jsonify({"status": "error", "message": "Missing 'region' or 'webhook_url' in payload"}), 400
        
    region = data['region']
    url = data['webhook_url']
    
    # 4. To ensure the key matches the region they are trying to access
    assigned_region = AUTHORIZED_API_KEYS[token]
    if assigned_region.lower() != region.lower():
        return jsonify({
            "status": "error", 
            "message": f"Security breach detected. This API key is not authorized to manage alerts for {region}."
        }), 403

    # Save their connection to our database
    registered_webhooks[region] = url
    
    return jsonify({
        "status": "success", 
        "message": f"Successfully authenticated. {region} will now receive emergency CAP alerts at {url}"
    }), 200