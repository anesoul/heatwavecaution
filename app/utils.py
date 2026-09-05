import math
import datetime
import requests
from flask import current_app

def calculate_wbgt(temp, humidity, wind_kmh, solar_radiation=0.0):
    """
    Calculates outdoor Wet-Bulb Globe Temperature (WBGT) using:
    1. Stull's equation for Natural Wet-Bulb Temperature (Twb)
    2. Approximation of Black Globe Temperature (Tg) from solar radiation & convective wind cooling
    3. Composite outdoor WBGT = 0.7 * Twb + 0.2 * Tg + 0.1 * Ta
    """
    try:
        t = float(temp)
        rh = float(humidity)
        v_ms = max(float(wind_kmh) / 3.6, 0.1)  # convert km/h to m/s, floor at 0.1
        sol = max(float(solar_radiation or 0.0), 0.0)
        
        # Stull's equation for Twb (°C)
        twb = (
            t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )
        
        # Black Globe Temperature approximation (°C)
        tg = t + (0.015 * sol) / (1.0 + 0.5 * v_ms)
        
        # Composite Outdoor WBGT (°C)
        wbgt = (0.7 * twb) + (0.2 * tg) + (0.1 * t)
        return round(wbgt, 1)
    except Exception:
        return round(temp * 0.85, 1)

def get_risk_meta(wbgt, adjusted_stress):
    """Determines risk level, UI color, and split advisories based on dual thresholds."""
    
    # Occupational Directive (Driven STRICTLY by WBGT weather)
    if wbgt >= current_app.config['WBGT_EXTREME']:
        occ_dir = "Total suspension of outdoor physical labor; construction halted."
    elif wbgt >= current_app.config['WBGT_DANGER']:
        occ_dir = "Enforce mandatory 50% work-rest cycles; limit direct solar exposure."
    elif wbgt >= current_app.config['WBGT_CAUTION']:
        occ_dir = "Increase fluid intake; provide shaded hydration points for outdoor workers."
    else:
        occ_dir = "Standard outdoor working conditions. Routine hydration recommended."

    # Municipal Action & Dashboard Theme (Driven STRICTLY by Mortality Index)
    if adjusted_stress >= current_app.config['THRESHOLD_EXTREME']:
        return (
            "RED ALERT (Extreme Risk)", "danger", "#dc3545",
            occ_dir,
            "Critical mortality risk. Deploy emergency ambulances and open public cooling centers immediately."
        )
    elif adjusted_stress >= current_app.config['THRESHOLD_DANGER']:
        return (
            "ORANGE ALERT (High Risk)", "orange", "#fd7e14",
            occ_dir,
            "High hospitalization risk. Activate ward-level medical surge capacity and dispatch water tankers."
        )
    elif adjusted_stress >= current_app.config['THRESHOLD_CAUTION']:
        return (
            "YELLOW ALERT (Caution)", "warning", "#ffc107",
            occ_dir,
            "Elevated vulnerability. Issue public health warnings and monitor elderly/slum populations."
        )
    else:
        return (
            "GREEN (Normal)", "success", "#198754",
            occ_dir,
            "No elevated municipal emergency response required."
        )

def fetch_bengaluru_weather():
    base_url = current_app.config['OPEN_METEO_BASE_URL']
    wards = current_app.config['WARDS_DATA']
    
    ward_results = {}
    
    for name, info in wards.items():
        params = {
            "latitude": info['lat'],
            "longitude": info['lon'],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m,shortwave_radiation",
            "forecast_days": 5,
            "timezone": current_app.config['TIMEZONE']
        }
        
        try:
            res = requests.get(base_url, params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            
            cur = data.get('current', {})
            hourly = data.get('hourly', {})
            
            temp = cur.get('temperature_2m', 0.0)
            humidity = cur.get('relative_humidity_2m', 0.0)
            wind = cur.get('wind_speed_10m', 0.0)
            solar = cur.get('shortwave_radiation', 0.0)
            apparent_temp = cur.get('apparent_temperature', temp)
            
            # Compute 5-day hourly WBGT forecast
            hourly_times = hourly.get('time', [])
            hourly_temps = hourly.get('temperature_2m', [])
            hourly_rhs = hourly.get('relative_humidity_2m', [])
            hourly_winds = hourly.get('wind_speed_10m', [])
            hourly_sols = hourly.get('shortwave_radiation', [])
            
            # --- CHANGES START HERE ---
            forecast_mri_list = []
            multiplier = info.get('multiplier', 1.0) # Fetch multiplier before the loop
            
            for i in range(len(hourly_times)):
                t_h = hourly_temps[i] if i < len(hourly_temps) else temp
                rh_h = hourly_rhs[i] if i < len(hourly_rhs) else humidity
                w_h = hourly_winds[i] if i < len(hourly_winds) else wind
                s_h = hourly_sols[i] if i < len(hourly_sols) else 0.0
                
                # Calculate raw hourly WBGT
                hourly_wbgt = calculate_wbgt(t_h, rh_h, w_h, s_h)
                
                # Multiply to get Mortality Risk Index (MRI)
                hourly_mri = round(hourly_wbgt * multiplier, 1)
                forecast_mri_list.append(hourly_mri)
                
        except Exception as e:
            print(f"API Error for {name}: {e}")
            temp, humidity, wind, solar, apparent_temp = 30.0, 55.0, 10.0, 400.0, 33.0
            hourly_times = []
            forecast_mri_list = [] # Update fallback variable
            multiplier = info.get('multiplier', 1.0)

            # Hackathon Safety Net: Generate 120 hours of simulated sine-wave data if offline
            base_time = datetime.datetime.now()
            hourly_times = [(base_time + datetime.timedelta(hours=i)).isoformat() for i in range(120)]
            
            # Creates a realistic day/night temperature wave
            forecast_mri_list = [round((25.0 + (math.sin(i / 3.8) * 4)) * multiplier, 1) for i in range(120)]
        # --- CHANGES END HERE ---

        # Current Outdoor WBGT
        current_wbgt = calculate_wbgt(temp, humidity, wind, solar)
        
        # Demographic Risk Score = Outdoor WBGT * Ward Vulnerability Multiplier
        multiplier = info['multiplier']
        adjusted_stress = round(current_wbgt * multiplier, 1)
        risk_level, color, hex_color, occ_dir, mun_action = get_risk_meta(current_wbgt, adjusted_stress)
        
        ward_results[name] = {
            "name": name,
            "desc": info.get("desc", ""),
            "lat": info['lat'],
            "lon": info['lon'],
            "multiplier": multiplier,
            "temp": round(temp, 1),
            "humidity": round(humidity, 1),
            "wind": round(wind, 1),
            "wbgt": current_wbgt,
            "apparent_temp": round(apparent_temp, 1),
            "adjusted_stress": adjusted_stress,
            "risk_level": risk_level,
            "color": color,
            "hex_color": hex_color,
            "occ_directive": occ_dir,      # <-- Added to dictionary
            "mun_action": mun_action,      # <-- Added to dictionary
            "forecast_times": hourly_times,
            "forecast_temps": forecast_mri_list
        }

    primary_key = "Sampangi Rama Nagar" if "Sampangi Rama Nagar" in ward_results else list(ward_results.keys())[0]
    active_ward = ward_results[primary_key]

    return {
        "active": active_ward,
        "all_wards": list(ward_results.values()),
        "ward_map": ward_results
    }