import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

    CITY_NAME = "Bengaluru"
    DEFAULT_LAT = 12.9716
    DEFAULT_LON = 77.5946
    TIMEZONE = "Asia/Kolkata"

    # API Endpoints
    OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
    
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
    NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    
    # Using multiple mirrors to bypass strict firewalls
    OVERPASS_MIRRORS = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]

    # Official Occupational WBGT Thresholds (°C) - For display/reference only
    WBGT_CAUTION = 30.0
    WBGT_DANGER = 32.0
    WBGT_EXTREME = 34.0

    # Mortality Risk Index (MRI) Thresholds - Drives the Dashboard Colors & Alerts
    THRESHOLD_CAUTION = 30.0  
    THRESHOLD_DANGER = 38.0   
    THRESHOLD_EXTREME = 51.0  

    '''
    # Demographic Vulnerability Multipliers
    # Swapped to 'fallback_multiplier' for safety if the live OSM API fails during demo
    WARDS_DATA = {
        "Sampangi Rama Nagar": {
            "lat": 12.9716, 
            "lon": 77.5946, 
            "fallback_multiplier": 0,
            "desc": "Baseline urban canopy (Cubbon Park zone)"
        },
        "Chickpet": {
            "lat": 12.9710, 
            "lon": 77.5764, 
            "fallback_multiplier": 1.6,
            "desc": "High outdoor labor density & commercial markets"
        },
        "Peenya": {
            "lat": 13.0329, 
            "lon": 77.5273, 
            "fallback_multiplier": 1.5,
            "desc": "Industrial corridor, low tree cover"
        },
        "Whitefield": {
            "lat": 12.9698, 
            "lon": 77.7500, 
            "fallback_multiplier": 0.8,
            "desc": "IT corridor, predominantly indoor climate control"
        }
    }
    '''

    # Twilio/SMS Credentials (optional, pulled from env if used)
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')
    ALERT_TO_NUMBER = os.environ.get('ALERT_TO_NUMBER')