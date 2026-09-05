import os 

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

    CITY_NAME = "Bengaluru"
    DEFAULT_LAT = 12.9716
    DEFAULT_LON = 77.5946
    TIMEZONE = "Asia/Kolkata"

    # API Endpoints
    OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Official Occupational WBGT Thresholds (°C) - For display/reference only
    WBGT_CAUTION = 28.0
    WBGT_DANGER = 30.0
    WBGT_EXTREME = 32.0

    # Mortality Risk Index (MRI) Thresholds - Drives the Dashboard Colors & Alerts
    # Scaled baseline: < 28 (Green), 28-35 (Yellow), 35-50 (Orange), 50+ (Red)
    THRESHOLD_CAUTION = 28.0  # Yellow: Elevated Risk
    THRESHOLD_DANGER = 35.0   # Orange: Hospitalization Spikes Begin
    THRESHOLD_EXTREME = 50.0  # Red: Critical Risk/Mortality Spikes

    # Demographic Vulnerability Multipliers
    # 1.0 is the baseline; higher means greater risk of hospitalization
    WARDS_DATA = {
        "Sampangi Rama Nagar": {
            "lat": 12.9716, 
            "lon": 77.5946, 
            "multiplier": 1.0,
            "desc": "Baseline urban canopy (Cubbon Park zone)"
        },
        "Chickpet": {
            "lat": 12.9710, 
            "lon": 77.5764, 
            "multiplier": 1.6,
            "desc": "High outdoor labor density & commercial markets"
        },
        "Peenya": {
            "lat": 13.0329, 
            "lon": 77.5273, 
            "multiplier": 1.5,
            "desc": "Industrial corridor, low tree cover"
        },
        "Whitefield": {
            "lat": 12.9698, 
            "lon": 77.7500, 
            "multiplier": 0.8,
            "desc": "IT corridor, predominantly indoor climate control"
        }
    }

   # Twilio/SMS Credentials (optional, pulled from env if used)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')
    ALERT_TO_NUMBER = os.environ.get('ALERT_TO_NUMBER')